import sys
import random
import json
import logging
import datetime
import pickle
from flask import Flask, request, jsonify
from modules.cloudevent import CloudEventService
from modules.mqtt import MQTTClient

print(sys.argv)
if(len(sys.argv) < 4):
    print('Missing argument: please inform the broker address, port and topic')
    exit()

broker_address = str(sys.argv[1])
broker_port = int(sys.argv[2])
topic = str(sys.argv[3])
topic_response = str(sys.argv[4])

if(len(sys.argv) > 5):
    n_iteration = int(sys.argv[5])
else:
    n_iteration = 100

source = "edge-service"
message_type = "edge-service-message"
data = { "edge-service": "edge-service-data" }
client_id = f'python-mqtt-{random.randint(0, 1000)}'

#broker_address = "192.168.1.195"
#broker_port = 1883
#topic = "mytopic-response"

app = Flask(__name__)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

mlp_model = pickle.load(open('model/mlp.model', 'rb'))

def extract_sensor_data(payload):
    data = [
        payload['type'],
        payload['air_temperature'],
        payload['process_temperature'],
        payload['rotational_speed'],
        payload['torque'],
        payload['tool_wear'],
        payload['twf'],
        payload['hdf'],
        payload['pwf'],
        payload['osf'],
        payload['rnf'],
    ]
    return data

def score(payload):

    start_time = datetime.datetime.now()

    app.logger.info(payload)
    
    data = extract_sensor_data(payload)

    for _ in range(0, n_iteration):
        result = mlp_model.predict([data])

    end_time = datetime.datetime.now()

    app.logger.info("Predict Result: " + str(result[0]))

    return {"result": int(result[0]), "processing_time": str(end_time - start_time)}

@app.route("/", methods=["POST"])
def home():

    start_time = datetime.datetime.now()

    cloud_event = CloudEventService()
    event = cloud_event.receive_message(request)

    data = extract_sensor_data(event.data['sensor'])
    
    for _ in range(0, n_iteration):
        result = mlp_model.predict([data])

    app.logger.info("Predict Result: " + str(result[0]))

    # Process event

    # app.logger.info(
    #    f"Found {event['id']} from {event['source']} with type "
    #    f"{event['type']} and specversion {event['specversion']}"
    #)

    now = datetime.datetime.now()
    sent_datetime = datetime.datetime.strptime(event.data['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
    latency = str(now - sent_datetime)

    app.logger.info(
        f"Event Priority: {event.data['priority']} | "
        # f"Data Content: {event.data['message']} bytes | "
        f"Data Length: {len(event.data['message'])} bytes | "
        # f"Sent time: {sent_datetime} -"
        # f"Now: {now} -"
        f"Latency: {latency}"
    )

    end_time = datetime.datetime.now()

    event.data["processing_time"] = str(end_time - start_time)

    mqtt_client.publish(json.dumps(event.data))

    # Return 204 - No-content
    return "", 204

if __name__ == "__main__":
    mqtt_client = MQTTClient(client_id=client_id, broker=broker_address, port=broker_port, topic=topic, topic_response=topic_response)
    mqtt_client.connect_mqtt()
    mqtt_client.subscribe(score)
    app.logger.info("Starting up server...")
    app.run(host='0.0.0.0', port=8080)
