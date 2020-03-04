import time
from datetime import datetime, timezone, timedelta

import requests

API_key = "f286b66e96a9c25798f3773500d98aa6865111ce"

PROJECTS = {
    "API": "247492",
    "MT": "246831"
}

START_TIME = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
LIMIT = 1000

TIMEZONE_CONVERSTIONS = {
    "PST": 8,
    "CST": 6
}

PARAMS = {"start_time": START_TIME, "limit": LIMIT, "token": API_key}

#### For each project specified at the top, we will look for that project's groups (errors), and for each of those groups, we will look for notices (occurrences).
#### The notices will then be written into a .csv file, with the columns "Project", "Group ID", "Occurrence ID", "Timestamp", "Message" and "Browser".

result = open("Airbrake Report.csv", "a")
# result.write("Project;Group ID;Occurrence ID;Timestamp;Message;Browser\n")
result.write("Project;Group ID;Occurrence ID;Timestamp;Message\n")

for project_name, project_id in PROJECTS.items():
    URL = "https://airbrake.io/api/v4/projects/"+project_id+"/groups"

    ### Make the request for a project's groups
    r = requests.get(url = URL, params = PARAMS)
    groupData = r.json()
    if groupData["count"]:
        for group in groupData["groups"]:
            URL = "https://airbrake.io/api/v4/projects/"+project_id+"/groups/"+group["id"]+"/notices"

            ## Make the request for a group's notices, with an appropriate amount of time to respect rate limits
            r = requests.get(url = URL, params = PARAMS)
            time.sleep(0.1)
            noticeData = r.json()
            row = {}

            ## If there are more notices than the limit set at the top (note that this caps at 1000), we will need to use pagination and a while loop to get all the results
            if noticeData["count"] > LIMIT:
                count = LIMIT
                page = 2
                while count < noticeData["count"]:
                    URL = "https://airbrake.io/api/v4/projects/"+project_id+"/groups/"+group["id"]+"/notices?page="+str(page)
                    new_request = requests.get(url = URL, params = PARAMS)
                    newData = new_request.json()
                    noticeData["notices"] += newData["notices"]
                    count += len(newData["notices"])
                    page += 1

            ## Sorting through the response json and writing it to the file
            for notice in noticeData["notices"]:
                row["groupId"] = notice["groupId"]
                row["id"] = notice["id"]
                
                # "createdAt" seems to be where the desired timestamp can be found for all notices found so far
                if "createdAt" in notice:
                    # most timestamps follow the try format, with some exceptions (hence the except)
                    try:
                        dt = (datetime.strptime(notice["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ")) - timedelta(hours=TIMEZONE_CONVERSTIONS["PST"])
                    except:
                        dt = (datetime.strptime(notice["createdAt"], "%Y-%m-%dT%H:%M:%SZ")) - timedelta(hours=TIMEZONE_CONVERSTIONS["PST"])
                    row["createdAt"] = dt.strftime("%m/%d/%y %H:%M")

                # Regrettably, the two projects searched so far structure their json data differently, hence the different ways of finding "User-Agent"
                if project_name == "API":
                    if "extra" in notice["params"] and "inbound_headers" in notice["params"]["extra"] and "User-Agent" in notice["params"]["extra"]["inbound_headers"]:
                        row["browser"] = notice["params"]["extra"]["inbound_headers"]["User-Agent"].replace(",", "")
                    else:
                        row["browser"] = "None"
                elif project_name == "MT":
                    row["browser"] = notice["context"]["userAgent"].replace(",", "")

                # Find the error message, if any
                if "message" in notice["errors"][0]:
                    row["message"] = notice["errors"][0]["message"].replace(",", "").replace("\n", "")
                else:
                    row["message"] = "None"
                
                # Also regrettably, not all messages are necessarily writable to csv smoothly. The workaround so far has been to print those (thankfully limited) cases out in the CLI and manually transfer those to the file- if you feel like changing this, go for it!
                # And finally, in order to stop Excel from dropping trailing digits from IDs, "DONOTTRUNCATE" leads all the ids to force it through as text- a simple find and replace with "'" should fix that once in Excel.
                try:
                    # result.write(project_name+",DONOTTRUNCATE"+row["groupId"]+",DONOTTRUNCATE"+(row["id"])+","+row["createdAt"]+","+str(row["message"])+","+row["browser"]+"\n")
                    result.write(project_name+";"+row["groupId"]+";"+(row["id"])+";"+row["createdAt"]+";"+str(row["message"])+"\n")

                except:
                    print(project_name)
                    print(row["id"])
                    # print(project_name+",DONOTTRUNCATE"+row["groupId"]+",DONOTTRUNCATE"+(row["id"])+","+row["createdAt"]+","+str(row["message"])+","+row["browser"]+"\n")
                    print(project_name+";"+row["groupId"]+";"+(row["id"])+";"+row["createdAt"]+";"+str(row["message"])+"\n")