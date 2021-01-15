import json
import os

import boto3
import requests
from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, CallbackContext, Filters, Dispatcher


def photos_only(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Please send me a photo")


def check_hotdog(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Analyzing... 🤔🤔🤔")
    # check if this photo received has a hotdog
    # get the file id
    file_id = update.message.photo.pop().file_id
    # generate a url where our bot can download the file
    file = context.bot.get_file(file_id)
    # download the file from telegram servers, upload a copy to our S3 bucket
    bucket_name = os.environ["BUCKET_NAME"]
    object_name = file.file_unique_id
    destination_object = boto3.resource("s3").Object(bucket_name, object_name)
    with requests.get(file.file_path, stream=True) as r:
        destination_object.put(Body=r.content)
    # send the image to rekognition and ask it to detect labels
    # user guide: https://docs.aws.amazon.com/rekognition/latest/dg/labels-detect-labels-image.html
    # api reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html#Rekognition.Client.detect_labels
    rekognition_client = boto3.client("rekognition")
    rekognition_response = rekognition_client.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket_name,
                "Name": object_name
            }
        }
    )
    # is there a hotdog?
    is_hotdog = False
    for label in rekognition_response["Labels"]:
        if label["Name"] == "Hot Dog":
            is_hotdog = True
            break
    if is_hotdog:
        update.message.reply_text("Congratulations! You found a hotdog!")
    else:
        update.message.reply_text("There is no hotdog :(")


bot = Bot(os.environ["BOT_TOKEN"])
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
dispatcher.add_handler(MessageHandler(Filters.photo, callback=check_hotdog))
dispatcher.add_handler(MessageHandler(Filters.text, callback=photos_only))


def lambda_handler(event, context):
    input_data = json.loads(event["body"])

    update = Update.de_json(input_data, bot)
    dispatcher.process_update(update)

    return {"statusCode": 200, "body": ""}
