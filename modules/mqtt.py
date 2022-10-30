import time
import logging
from paho.mqtt import client as paho_mqtt_client

logger = logging.getLogger('mqtt-client')
import logging
import time
import datetime
import json
import base64
from paho.mqtt import client as paho_mqtt_client

QOS_AT_MOST_ONCE=0
QOS_AT_LEAST_ONCE=1
QOS_EXACTLY_ONCE=2

class MQTTClient:

    def __init__(self, client_id, broker, port, topic, topic_response) -> None:
        self.mqttclient = paho_mqtt_client.Client(client_id)
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.topic = topic
        self.topic_response = topic_response
        self.message = { "timestamp": 1, "message": "", "image": "", "priority": 1}
        self.message_payload = self.generate_payload_size(10)
        self.logger = logging.getLogger("mqtt")
        self.logger.info("MQTT Client %s created", self.client_id)

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc) -> None:
            if rc == 0:
                self.logger.info("Connected to MQTT Broker on topic %s", self.topic)
            else:
                self.logger.error("Failed to connect to topic %s, return code %d\n", self.topic, rc)

        self.mqttclient.on_connect = on_connect
        self.mqttclient.connect(self.broker, self.port)
        return self.mqttclient
    
    def disconnect_mqtt(self):
        def on_disconnect():
            self.logger.info("Client disconnected")
        self.mqttclient.disconnect(on_disconnect)

    def generate_payload_size(self, nbytes):
        payload = "-"
        for i in range(nbytes):
            payload += "a"
        return payload

    def build_message(self, msg_count):
        msg = self.message
        msg["client_id"] = self.client_id
        msg["message"] = str(msg_count) + self.message_payload
        msg["image"] = self.image_payload
        msg["timestamp"] = datetime.datetime.now().isoformat()
        return json.dumps(msg)

    # n_messages: total amount of messages
    # message_period: period of time between each message (seconds)
    # high_priority_frequency: [0,1], percentage of priority 1 against priority 2 messages
    def publish(self, n_messages, message_period):
        msg_count = 0
        while n_messages > msg_count:
            time.sleep(message_period)
            msg = self.build_message(msg_count=msg_count)
            result = self.mqttclient.publish(self.topic, msg)
            status = result[0]
            if status != 0:
                self.logger.error(f"Failed to send in client {self.client_id} message to topic {self.topic}")
                msg["image"] = ""
                self.logger.error(f"Failed to send `{msg}` to topic `{self.topic}`")
                self.logger.error(result)
            #else:
            #    self.logger.info(f"Send `{msg}` to topic `{self.topic}`")
            msg_count += 1
            if msg_count%100:
                self.logger.info("Client %s still alive", self.client_id)

    def subscribe(self, callback):
        def on_message(client, userdata, msg):
            msg_dict = json.loads(msg.payload)
            now = datetime.datetime.now()
            sent_datetime = datetime.datetime.strptime(msg_dict['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
            latency = str(now - sent_datetime)
            if "processing_time" in msg_dict:
                self.logger.info(f"Received message from `{msg_dict['client_id']}` with latency `{latency}` at `{now}` | Processing time: `{msg_dict['processing_time']}`")
            else:
                self.logger.info(f"Received message from `{msg_dict['client_id']}` with latency `{latency}` at `{now}`")

            response = callback(msg_dict['sensor'])
            msg_dict["processing_time"] = response["processing_time"]
            msg_dict["result"] = response["result"]
            print("Response: ")
            print(json.dumps(msg_dict))
            self.mqttclient.publish(self.topic_response, json.dumps(msg_dict), qos=QOS_EXACTLY_ONCE)

        self.mqttclient.subscribe(self.topic, qos=QOS_EXACTLY_ONCE)
        self.mqttclient.on_message = on_message
        self.mqttclient.loop_forever()