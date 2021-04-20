# -*- coding: utf-8 -*-
import time

from .solve import solve
from app import celery_app
from app.utils import slogger

# example from https://github.com/WileyIntelligentSolutions/wiley-dash-boilerplate2
# import boto3

# This is the function that will be run by Celery
# You need to change the function declaration to include all the
# arguments that the app will pass to the function:


@celery_app.task(bind=True)
def query(self, l1, l2, data):
    task_id = self.request.id
    slogger("query", "query in progress, task_id={}".format(task_id))
    # Don't touch this:
    self.update_state(state="PROGRESS")
    time.sleep(1.5)  # a short dwell is necessary for other async processes to catch-up
    # Change all of this to whatever you want:
    results = solve(l1, l2, data)
    slogger("query", "check results and process if necessary")
    # Only write an Excel file for download if there were actual results
    # if len(results) > 0:
    #     # Save locally in Excel format then copy the file to S3 because any local
    #     # files store locally in the container are highly volatile and
    #     # will likely be deleted before the user has a chance to download
    #     reports_folder = os.path.join(
    #         os.path.dirname(os.path.realpath(__file__)), "reports"
    #     )
    #     # Use the Celery task id as the filename (we change it to something more
    #     # userfriendly later)
    #     filename = f"{task_id}.csdf"
    #     # excel_filename = "{}.xlsx".format(task_id)
    #     local_excel_path = os.path.join(reports_folder, filename)
    #     # slogger("query", f"saving full report locally as {local_excel_path}")
    #     # excel_writer = pd.ExcelWriter(local_excel_path, engine="xlsxwriter")
    #     # # Here you can customize the name of the Excel sheet:
    #     # pd.DataFrame(results).to_excel(
    #     #     excel_writer, sheet_name="BoilerplateResults", index=False
    #     # )
    #     # excel_writer.save()

    #     # Copy to S3 if enabled
    #     # if config.DISABLE_S3 == False:
    #     #     bucket_name = os.environ["S3_BUCKET_NAME"]
    #     #     # We prefix the S3 key with the name of the app - you can change this if
    #     #       you want:
    #     #     s3_excel_key = "{}/{}".format(config.DASH_APP_NAME, excel_filename)
    #     #     slogger(
    #     #         "query",
    #     #         "copying {} to S3 bucket {} with key {}".format(
    #     #             local_excel_path, bucket_name, s3_excel_key
    #     #         ),
    #     #     )
    #     #     client = boto3.client(
    #     #         "s3",
    #     #         aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    #     #         aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
    #     #     )
    #     #     body = open(local_excel_path, "rb")
    #     #     client.put_object(Bucket=bucket_name, Key=s3_excel_key, Body=body)
    #     # else:
    #     slogger(
    #         "query",
    #         "caution - S3 is disabled so the Download Excel link will be broken!",
    #     )
    # else:
    slogger("query", "empty results - nothing was saved")

    # Return results for display
    slogger("query", "return results")
    return results
