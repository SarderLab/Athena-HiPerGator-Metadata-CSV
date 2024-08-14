
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

def urlAndCredentials(instance):
    UserOrCollectionIDs = None
    cookie=''
    if(instance == 'athena'):
        api_url='https://athena.rc.ufl.edu/api/v1/'
        api_key='0Da69IGX29DAl1JGyS8nZ1nSRxIS4LlgnWVUMWko'
        dest_dir = os.path.join(script_dir, 'Athena')
        if len(sys.argv) > 2:
            UserOrCollectionIDs = sys.argv[2]

        if len(sys.argv) > 3:
            directory_info = sys.argv[3]
            dest_dir = os.path.join(directory_info, 'Athena')

    else:
        api_url='https://devathena.rc.ufl.edu/api/v1/'
        api_key='gjdij9NkV7RN1qz7uqXyramjmOXAdh9jDAznN5AL'
        #Get cookie from user
        #cookie = sys.argv[2]
        dest_dir = os.path.join(script_dir, 'DevAthena')
        if len(sys.argv) > 2:
            UserOrCollectionIDs = sys.argv[2]

        if len(sys.argv) > 3:
            directory_info = sys.argv[3]
            dest_dir = os.path.join(directory_info, 'DevAthena')

    if UserOrCollectionIDs == "all":
        UserOrCollectionIDs = None

   
    return  api_url, api_key, dest_dir, cookie, UserOrCollectionIDs
    