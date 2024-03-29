import os
import time
import subprocess
import re

import tiktoken
import openai
import dotenv

dotenv.load_dotenv()
OPENAI_API_TYPE = os.getenv('OPENAI_API_TYPE', '')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION', '') 
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', '') 
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '') 

# print('env:', OPENAI_API_TYPE, OPENAI_API_VERSION, OPENAI_API_BASE, OPENAI_API_KEY)
openai.api_type = OPENAI_API_TYPE
openai.api_version = OPENAI_API_VERSION
openai.api_base = OPENAI_API_BASE
openai.api_key = OPENAI_API_KEY

max_response_tokens = 250
token_limit= 4096

# def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
#     encoding = tiktoken.encoding_for_model(model)  # seems fail to connect in INX
#     num_tokens = 0
#     for message in messages:
#         num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
#         for key, value in message.items():
#             num_tokens += len(encoding.encode(value))
#             if key == "name":  # if there's a name, the role is omitted
#                 num_tokens += -1  # role is always required and always 1 token
#     num_tokens += 2  # every reply is primed with <im_start>assistant
#     return num_tokens

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            # num_tokens += len(str(value).split())
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def init_converstation():
    system_message = {
        "role": "system", 
        "content": """You are a translator to translate nature language to powershell commands.
請直接給我code，不須任何文字說明和markdown的format。"""
        }
    conversation = []
    conversation.append(system_message)
    return conversation



def get_response(conversation, max_response_tokens):

    response = openai.ChatCompletion.create(
                engine="gpt-35-turbo", # The deployment name you chose when you deployed the ChatGPT or GPT-4 model.
                messages = conversation,
                temperature=.7,
                max_tokens=max_response_tokens,
            )
    return response

def is_allowed_powershell_command(command):
    # 列出允許的 PowerShell 命令
    allowed_commands = [
        'Get-Process',
        'Get-Service',
        'Get-Date',
        # 加入你想允許的命令
    ]
    
    # 檢查 command 是否在允許的列表中
    for allowed_command in allowed_commands:
        if command.startswith(allowed_command):
            return True
            
    # 如果 command 不在允許的列表中，返回 False
    return False

pat = re.compile(r'^[a-zA-Z0-9]')
def filter2(cmd: str):
    return '\n'.join(filter(lambda x: bool(pat.search(x)) , cmd.splitlines()))


def run_powershell_command(command):
    # command = '\n'.join(filter(is_allowed_powershell_command, command.splitlines()))
    command = filter2(command)
    try:
        process = subprocess.Popen(["powershell", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # return f"Command exited with error {process.returncode}: {error.decode('utf-8')}"
            return f"Command exited with error {process.returncode}: {error.decode('cp950')}"
        else:
            # return output.decode('utf-8')
            return output.decode('cp950')

    except Exception as e:
        return str(e)


def main():
    conversation = init_converstation()
    while(True): 
        time.sleep(0.5)
        user_input = input(">>> ")
        if user_input == 'exit':
            break
        elif user_input.strip() == '':
            continue
        else:
            if user_input.startswith(':'):
                user_input = user_input.lstrip(':')
                        
                conversation.append({"role": "user", "content": user_input})
                conv_history_tokens = num_tokens_from_messages(conversation)

                while (conv_history_tokens + max_response_tokens >= token_limit):
                    del conversation[1] 
                    conv_history_tokens = num_tokens_from_messages(conversation)
                
                try:    
                    response = get_response(conversation, max_response_tokens)
                except openai.error.APIConnectionError:
                    time.sleep(3)
                    print('not responding, retry...')
                    response = get_response(conversation, max_response_tokens)
                    

                conversation.append({"role": "assistant", "content": response['choices'][0]['message']['content']})
                cmdstr = response['choices'][0]['message']['content']
                print("\n" + cmdstr + '\n---------------------------------------------\n' + run_powershell_command(cmdstr))
                
                
            else:
                cmdstr = user_input
                print("\n" + cmdstr + '\n---------------------------------------------\n' + run_powershell_command(cmdstr))
                
                
if __name__ == '__main__':
    main()
