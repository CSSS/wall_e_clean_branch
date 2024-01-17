#!/usr/bin/python3

import json
import re
import subprocess
import sys
import time

import requests

# commands to run to setup python on jenkins docker container
# sudo apt-get install -y python3
# sudo apt-get install wget
# wget https://bootstrap.pypa.io/get-pip.py
# sudo apt install python3-distutils
# python3 get-pip.py
DISCORD_TOKEN = sys.argv[1]
header = {
    "Authorization": f"Bot {DISCORD_TOKEN}"
}

DISCORD_CHANNEL_SUFFIXES = ["_logs", "_bot_channel", "_council", "_mod_channel", "_announcements"]

_, output = subprocess.getstatusoutput("docker images 'test_*'")
docker_image_names = {
    docker_image_name.split("   ")[0].strip(): docker_image_name.split("   ")[-3].strip()
    for docker_image_name in output.split("\n")[1:]
}

_, output = subprocess.getstatusoutput("docker ps -a --filter 'name=TEST_' --format 'table {{.Names}}'")
docker_container_names = output.split("\n")[1:]

current_prs = [
    f"pr-{pr['number']}"
    for pr in json.loads(requests.get("https://api.github.com/repos/CSSS/wall_e/pulls?state=open").text)
]
current_branches = [
    branch['name']
    for branch in json.loads(requests.get("https://api.github.com/repos/CSSS/wall_e/branches").text)
]

branches_to_remove = []
channels_to_keep = []
for docker_container_name in docker_container_names:
    print(f"iterating through container name [{docker_container_name}]")
    if re.search(r'_wall_e_db$', docker_container_name):
        print(f"processing container name {docker_container_name}")
        branch_name = docker_container_name[5:-10]
        branch_name_lower_case = branch_name.lower()
        print(f"branch is set to [{branch_name}]")
        if branch_name not in current_prs and branch_name not in current_branches:
            print(f"branch [{branch_name}] is valid to remove")
            branches_to_remove.append(branch_name)
        else:
            channels_to_keep.append(branch_name_lower_case)
            channels_to_keep.extend([
                f"{branch_name_lower_case}{discord_channel_suffix}"
                for discord_channel_suffix in DISCORD_CHANNEL_SUFFIXES
            ])

successful = False
retry_limit = 5
attempt = 0
guild_id = None

while (not successful) and (attempt < retry_limit):
    url = "https://discordapp.com/api/users/@me/guilds"
    response = requests.get(url, headers=header)
    status_code = response.status_code
    response_body = json.loads(response.text)
    if status_code == 200:
        successful = True
        guild_id = response_body[0]['id']
    elif status_code == 429:
        attempt += 1
        print(f"GET {url}")
        print(response_body.get("message", None))
        retry_after = response_body.get('retry_after', None)
        if retry_after is not None:
            time.sleep(float(retry_after))
    else:
        print(f"GET {url}")
        print(json.dumps(response.json(), indent=4))
        attempt += 1
        time.sleep(5)


successful = False
retry_limit = 5
attempt = 0

channels = []

while (not successful) and (attempt < retry_limit):
    url = f"https://discordapp.com/api/guilds/{guild_id}/channels"
    response = requests.get(url, headers=header)
    status_code = response.status_code
    response_body = json.loads(response.text)
    if status_code == 200:
        successful = True
        channels = response_body
    elif status_code == 429:
        attempt += 1
        print(f"GET {url}")
        print(response_body.get("message", None))
        retry_after = response_body.get('retry_after', None)
        if retry_after is not None:
            time.sleep(float(retry_after))
    else:
        print(f"GET {url}")
        print(json.dumps(response.json(), indent=4))
        attempt += 1
        time.sleep(5)

for channel in channels:
    channel_name = channel.get("name", None)
    if channel_name not in channels_to_keep:
        url = f"https://discordapp.com/api/channels/{channel['id']}"
        response = requests.delete(url, headers=header)
        print(f"DELETE {url}")
        print(json.dumps(response.json(), indent=4))

for branch_to_remove in branches_to_remove:
    with open("clear_docker_resources.sh", "w") as f:
        f.write(f"""
#!/bin/bash
export COMPOSE_PROJECT_NAME="TEST_{branch_to_remove}"
export container_name=$(echo "${{COMPOSE_PROJECT_NAME}}"_wall_e)
export db_container_name=$(echo "${{COMPOSE_PROJECT_NAME}}"_wall_e_db)
export image_name=$(echo "${{COMPOSE_PROJECT_NAME}}"_wall_e | awk '{{print tolower($0)}}')
export network_name=$(echo "${{COMPOSE_PROJECT_NAME}}"_wall_e_network | awk '{{print tolower($0)}}')
export volume_name="${{COMPOSE_PROJECT_NAME}}_logs"
        
docker rm -f "${{container_name}}" "${{db_container_name}}"
docker volume rm "${{volume_name}}" || true
docker image rm "${{image_name}}" || true
docker network rm "${{network_name}}" || true
""")
    _, output = subprocess.getstatusoutput("bash  clear_docker_resources.sh")
    print(output)
