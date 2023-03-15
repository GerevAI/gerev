# Google drive

## Setting up

The process involves creating a service account with an email address, then sharing drive folders with that service account.

1. Go to [Create a project](https://console.cloud.google.com/projectcreate?previousPage=%2Fprojectselector2%2Fiam-admin%2Fserviceaccounts%2Fcreate) on google cloud console. Choose a name and organization (you can also leave organization empty)

![Create a project](./create-new-project.png)

2. Wait for loading to finish, you should be redirected to the 'create a service account' page. 

![Wait for loading to finish](./loading-screen.png)

3. Select a name for the account. The rest of the fields don't matter, you can press done at the bottom.

![Create service account](./create-service-account.png)

4. hover over the newly created service account and copy the email address and save it.

![Copy email address](./copy-email.png)

5. click the newly created service account, then go to the KEYS tab

![KEYS tab](./keys-tab.png)

6. click ADD KEY -> Create new key and Select JSON. It should download a json file.

![Create a key](./create-key.png)

![Select JSON](./create-key-json.png)

7. Go to [Google Drive](https://drive.google.com/) and share the google drive folders you want to index with the service account email

![Share drive folder](./google-drive-share.png)

![Share drive folder with the service account](./share-drive-folder.png)

7. copy the contents of the json file into the box in the Gerev settings panel