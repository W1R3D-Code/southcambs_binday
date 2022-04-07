# South Cambridge Bin day

Just a simple Azure Function that runs daily, grabbing the up-to-date bin collection schedule for a specific address useing the scambs.gov.uk waste calendar API; then sends you slack messages to reminder you the day before and the morning of.

By default the function will run at [8am daily](#functionjson), and if there is a bin collection the next day it will send you a reminder message imediately and schedule messages to remind you at 8:30pm that evening, and against at 7:30am the next day. Behaviour can be customised using [Application Settings](#application-settings).

The messages are simple and only contain which bin(s) to put out i.e. `Blue & Green bin day tomorrow`


***

# Running Locally

## Requirements

+ [Python 3.x](https://www.python.org/downloads/)
+ [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools) version 2.x or later

If you're using VS Code you'll need the following extensions (install the requirements above first and make sure they're included in your PATH):

+ [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
+ [Azure Functions](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)


Create a `local.settings.json` file in the same directory as `__init__.py`. See [Application Settings](#application-settings) for format and required config.

To run the function when debugging locally, add the following line to function.json `bindings` so that it runs imediately:

`"runOnStartup": true`


***


# Publish to Azure

For help on publishing see the Microsoft Docs: [Publish to Azure](https://docs.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code?tabs=csharp#publish-to-azure)

Once published you will need to configure your Application Settings as they are not copied from local.settings.json automatically.

You can use the `Azure Functions: Upload Local Setting` command in the command palette (Ctrl+Shift+P)
See [Application settings in Azure](https://docs.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code?tabs=python#application-settings-in-azure)


***

# Config


## function.json

To set when the function runs set the value of `schedule` in function.json

`schedule` must be a [CRON expression](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-python#ncrontab-expressions) or a [TimeSpan](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-python#timespan) value

Azure uses the [NCronTab](https://github.com/atifaziz/NCrontab) format. See free online [expression testers](https://ncrontab.swimburger.net/) for help



## Application Settings

When running locally these are the application settings you need in `local.settings.json`

```json
{
  "IsEncrypted": false,
  "Values": {
      "AzureWebJobsStorage": "UseDevelopmentStorage=true",
      "FUNCTIONS_WORKER_RUNTIME": "python",
      "ApiBaseUrl": "https://servicelayer3c.azure-api.net/wastecalendar",
      "Postcode": "<YOUR_POSTCODE>",
      "HouseNumber": <YOUR_HOUSENUMBER>,
      "ImmediateReminder": "<SEND_REMINDER_WHEN_FUNCTION_RUNS>",
      "DayBeforeReminderTime": "<TIME_TO_SEND_REMINDER_THE_DAY_BEFORE_COLLECTION>",
      "DayofReminderTime": "<TIME_TO_SEND_REMINDER_THE_DAY_OF_COLLECTION>",
      "SLACK_ACCESS_TOKEN": "<YOUR_SLACK_ACCESS_TOKEN>",
      "SLACK_USER_ID": "<YOUR_SLACK_USER_ID_TO_SEND_TO>"
    }
}
```

These Application Settings need to be configured when you deploy the Function


## Waste Calendar API Settings

These settings are used to call the Waste Calendar API used by South Cambridge Council

#### **ApiBaseUrl**
URL of Waste Calendar API e.g. https://servicelayer3c.azure-api.net/wastecalendar

#### **Postcode**
Postcode of the property you want to get waste collection dates for. NOTE: Exclude the space e.g. SW1A 2AA becomes `"SW1A2AA"`

#### **HouseNumber**
House number of the property you want to get waste collection dates for


## Reminder Preference Settings

### **ImmediateReminder**
Optional - Defaults to True

By default the function will run at **8am every day**;
If `ImmediateReminder` is set to `"True"` a reminder message will be sent when the function runs if a collection is the following day.
This is in addition to the scheduled message that evening and the next morning.

#### **DayBeforeReminderTime**
Optional - Defaults to 20:30
Time of day to schedule reminder the day before collection e.g. `"20:30"`

#### **DayofReminderTime**
Optional - Defaults to 07:30
Time of day to schedule reminder the day before collection e.g. `"07:30"`


## Slack Config Settings

#### **SLACK_ACCESS_TOKEN**
Access token for your slack workspace, see [Access Tokens](#access-tokens) below 

#### **SLACK_USER_ID**
Slack User ID of the user you want to send the reminder messages to, see [User ID](#user-id) below




***

# Slack Config

## Access Tokens

The provided access token can be a [Bot token](https://api.slack.com/authentication/token-types#bot) or a [User token](https://api.slack.com/authentication/token-types#user).

Creating a new Slack App / Bot is simple an can be done in a few clicks [here](https://api.slack.com/apps?new_app=1).
You can use the wizard or provide an App Manifest

e.g.

```yml
display_information:
  name: Bin Reminders
features:
  bot_user:
    display_name: Bin Reminders
    always_online: true
oauth_config:
  scopes:
    bot:
      - chat:write
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

To access your bot token first you need to have installed your app in a workspace, then navigate to **OAuth & Permissions** and scroll down to **OAuth Tokens for Your Workspace** where you should see your automatically generated **Bot User OAuth Token** (starts with `xoxb-`)

### Required OAuth Scopes

The function uses the following slack API calls to send messages and scheduled messages

[chat.postMessage](https://api.slack.com/methods/chat.postMessage)
[chat.scheduleMessage](https://api.slack.com/methods/chat.scheduleMessage)

In order to post messages in approved channels & conversations your bot requires the [chat:write](https://api.slack.com/scopes/chat:write) Scope.

Scopes can be configured on the OAuth & Permissions, accessible from the Features section 

## User ID

An individual's user ID can be found by clicking the `... More` button in a member's profile, then choosing `Copy member ID`.