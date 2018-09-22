import pika
import uuid
import base64

class VerifyToken(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='tokens',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)

if __name__ == "__main__":
    verifyToken_rpc = VerifyToken()
    token = "128e9c300e35b7dc723b130776eb91bc"
    mail = "adgil@ucm.es"
    passwd = "mypass"

    response1 = verifyToken_rpc.call(token)
    if response1 == 0:
        print("[DEBUG] Error. Invalid token")
    elif response1 == 1:
        print("[DEBUG] Error. Token has already been used.")
    else:
        #TODO: send credentials to register user
        #base64.b64encode(passwd)
        
    
