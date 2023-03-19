# Google drive

## Setting up

The process involves creating a service account with an email address, then sharing drive folders with that service account.

1. Go to [Create a project](https://console.cloud.google.com/projectcreate?previousPage=%2Fprojectselector2%2Fiam-admin%2Fserviceaccounts%2Fcreate) on google cloud console. It's important to choose your **organization** if you have one.

![Create a project](./create-project.png)

2. Enable [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) for the project

<!-- (https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com&redirect=https://console.cloud.google.com&_ga=2.116924806.1008578598.1678803320-418131787.1678643755) -->

3. Go to [Create a service account](https://console.cloud.google.com/projectselector/iam-admin/serviceaccounts/create?walkthrough_id=iam--create-service-account&_ga=2.83190934.1008578598.1678803320-418131787.1678643755#step_index=1) and select your project.

4. Select a name for the account. The rest of the fields don't matter, you can press done at the bottom.

![Create service account](./create-service-account.png)

5. hover over the newly created service account and copy the email address and save it.

![Copy email address](./copy-email.png)

6. click the newly created service account, then go to the KEYS tab

![KEYS tab](./keys-tab.png)

7. click ADD KEY -> Create new key and Select JSON. It should download a json file.

![Create a key](./create-key.png)

![Select JSON](./create-key-json.png)

8. Go to [Google Drive](https://drive.google.com/) and share the google drive folders you want to index with the service account email

![Share drive folder](./google-drive-share.png)

![Share drive folder with the service account](./share-drive-folder.png)

9. copy the contents of the json file into the box in the Gerev settings panel

![Gerev settings page](./gerev-settings.png)
