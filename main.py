import os
import re
import json

# TODO: Update to import real sdk package
import sys
sys.path.insert(0, 'C:/Users/ckoegel/Documents/sdks/bandwidth_python')
import bandwidth_python
from bandwidth_python.api.messages_api import MessagesApi
from bandwidth_python.api.media_api import MediaApi
from bandwidth_python.model.message_request import MessageRequest
from bandwidth_python.model.bandwidth_callback_message import BandwidthCallbackMessage
# ---------------------------------------------------

from fastapi import FastAPI, Request
from pydantic import BaseModel


BW_ACCOUNT_ID = os.environ.get('BW_ACCOUNT_ID')
BW_USERNAME = os.environ.get('BW_USERNAME')
BW_PASSWORD = os.environ.get('BW_PASSWORD')
BW_NUMBER = os.environ.get('BW_NUMBER')
BW_MESSAGING_APPLICATION_ID = os.environ.get('BW_MESSAGING_APPLICATION_ID')


class CreateBody(BaseModel):    # model for the received json body to create a message
    to: str
    text: str


configuration = bandwidth_python.Configuration(     # TODO: package name # Configure HTTP basic authorization: httpBasic
    username=BW_USERNAME,
    password=BW_PASSWORD
)


api_client = bandwidth_python.ApiClient(configuration)  # TODO: package name
messages_api_instance = MessagesApi(api_client)
media_api_instance = MediaApi(api_client)


app = FastAPI()


@app.post('/sendMessage')   # Make a POST request to this URL to send a text message.
def send_message(create_body: CreateBody):
    message_body = MessageRequest(
        to=[create_body.to],
        _from=BW_NUMBER,
        application_id=BW_MESSAGING_APPLICATION_ID,
        text=create_body.text
    )
    response = messages_api_instance.create_message(
        account_id=BW_ACCOUNT_ID,
        message_request=message_body,
        _return_http_data_only=False
    )

    return response[1]


@app.post('/callbacks/outbound/messaging/status') # This URL handles outbound message status callbacks.
async def handle_outbound_status(request: Request):
    status_body_array = await request.json()
    status_body = status_body_array[0]
    if status_body['type'] == "message-sending":
        print("message-sending type is only for MMS.")
    elif status_body['type'] == "message-delivered":
        print("Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.")
    elif status_body['type'] == "message-failed":
        print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
    else:
        print("Message type does not match endpoint. This endpoint is used for message status callbacks only.")

    return 200


@app.post('/callbacks/inbound/messaging')   # This URL handles inbound message callbacks.
async def handle_inbound(request: Request):
    inbound_body_array = await request.json()
    inbound_body = BandwidthCallbackMessage._new_from_openapi_data(inbound_body_array[0])
    print(inbound_body.description)
    if inbound_body.type == "message-received":
        print("To: {}\nFrom: {}\nText: {}".format(inbound_body.message.to[0], inbound_body.message._from,
                                                  inbound_body.message.text))
        
        if not hasattr(inbound_body.message, "media"):
            return 200

        for media in inbound_body.message.media:
            media_id = re.search('media/(.+)', media).group(1)
            media_name = media_id.split('/')[-1]
            if ".xml" not in media_id:
                filename = "./" + media_name
                downloaded_media = media_api_instance.get_media(BW_ACCOUNT_ID, media_id, _preload_content=False).data
                img_file = open(filename, "wb")
                img_file.write(downloaded_media)
                img_file.close()
    else:
        print("Message type does not match endpoint. This endpoint is used for inbound messages only.\nOutbound message status callbacks should be sent to /callbacks/outbound/messaging/status.")

    return 200


if __name__ == '__main__':
    app.run(host='0.0.0.0')
