#! /usr/bin/env python

import os
import pickle
from taskw import TaskWarrior
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from xdg import BaseDirectory

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LABEL = "gtd/next-action"

PKGNAME = 'task-gmail-sync'
CACHE_DIR = BaseDirectory.save_cache_path(PKGNAME)
TOKEN_PATH = os.path.join(CACHE_DIR, "token.pickle")
CREDENTIALS_PATH = os.path.join("/etc", PKGNAME, "credentials.json")

def initGmailService():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise ValueError("No credentials file found! Please install one at '{0}'".format(CREDENTIALS_PATH))
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)
    return service


service = initGmailService()


def extractSubject(msg):
    return next(
        (hdr["value"] for hdr in msg["payload"]["headers"] if hdr["name"] == "Subject"),
        None,
    )


def extractThreadSubject(thread):
    return extractSubject(thread["messages"][0])


def getLabelId():
    labels = service.users().labels().list(userId="me").execute()
    return next(label["id"] for label in labels["labels"] if label["name"] == LABEL)


def getTaskSubjects():
    label_id = getLabelId()

    actions = service.users().threads().list(labelIds=[label_id], userId="me").execute()
    getMessage = lambda id: service.users().messages().get(id=id, userId="me").execute()
    getThread = lambda id: service.users().threads().get(id=id, userId="me").execute()
    getSubject = lambda id: extractSubject(getThread(id))
    getThreadSubject = lambda id: extractThreadSubject(getThread(id))
    return [getThread(thread["id"]) for thread in actions["threads"]]
    # return [getThreadSubject(thread['id']) for thread in actions['threads']]


def syncTasks():
    threads = getTaskSubjects()

    w = TaskWarrior(marshal=True)
    tasks = w.filter_tasks({"tags.contains": "gmail"})

    for thread in threads:
        subject = extractThreadSubject(thread)
        task = next((task for task in tasks if task["description"] == subject), None)
        if task is None:
            # No associated TW task, create one
            task = w.task_add(subject, tags=["gmail"])
        else:
            # Remove found task from task list
            tasks.remove(task)

        # Make sure task is annotated with a gmail link
        annotation = "https://mail.google.com/mail/u/0/#inbox/{id}".format(
            id=thread["messages"][0]["id"]
        )
        if annotation not in task.get("annotations", []):
            w.task_annotate(task, annotation)

        # If this task was completed in TW, remove the label in gmail
        if task["status"] == "completed":
            # Remove label from gmail task
            print('"{0}" is complete! Removing label'.format(subject))
            service.users().threads().modify(
                userId="me", id=thread["id"], body={"removeLabelIds": [getLabelId()]}
            ).execute()

    # Any (pending) tasks left are a TaskWarrior task without a corresponding
    # subject This means the label was removed in gmail. Mark the task done.
    for task in tasks:
        if task["status"] == "pending":
            print(
                'Marking task "{0}" done because it\'s not labelled in gmail'.format(
                    task["description"]
                )
            )
            w.task_done(id=task["id"])


if __name__ == "__main__":
    syncTasks()
