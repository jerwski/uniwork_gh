# standard library
from ftplib import FTP
from pathlib import Path
from datetime import date
import http.client as client
from shutil import make_archive, unpack_archive

# django core
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from uniwork.settings import get_setting
from django.core.serializers import serialize
from django.core.management import call_command


# my models
from employee.models import Employee, EmployeeData, EmployeeHourlyRate
from evidence.models import WorkEvidence, EmployeeLeave, AccountPayment


# Create your archive functions here.


# archives paths
arch_dir = settings.ARCH_DIR
dest_path = settings.DEST_PATH
archive_root = settings.ARCHIVE_ROOT
archive_name = settings.ARCHIVE_NAME
archive_file = settings.ARCHIVE_FILE


def check_internet_connection()->bool:
    '''checks whether the internet is connected'''
    connect = client.HTTPConnection("www.google.com", timeout=5)
    try:
        connect.request("HEAD", "/")
        connect.close()
        return True
    except:
        connect.close()
        return False


def backup():
    '''total backup of database'''
    try:
        with archive_root.open('w') as jsonfile:
            call_command('dumpdata', indent=4, stdout=jsonfile)
    except FileNotFoundError as error:
        print(f'Something wrong... Error: {error}')


def mkfixture():
    '''create fixtures in json format'''
    year = date.today().year
    querys = {'employee': Employee.objects.all(),
              'employee data': EmployeeData.objects.all(),
              'employee hourly rate': EmployeeHourlyRate.objects.filter(update__year=year),
              'work evidence': WorkEvidence.objects.filter(start_work__year=year),
              'employee leave': EmployeeLeave.objects.filter(leave_date__year=year),
              'account payment': AccountPayment.objects.filter(account_date__year=year)}
    try:
        for app in ('employee', 'evidence'):
            models = apps.all_models[app]
            for model in models.values():
                with Path.cwd().joinpath(f'{dest_path}/{model._meta.model_name}.json').open('w') as fixture:
                    serialize('json', querys[f'{model._meta.verbose_name}'], indent=4, stream=fixture)
    except FileNotFoundError as error:
        print(f'Serialization error: {error}')


def readfixture(request):
    try:
        for file in list(Path.iterdir(dest_path)):
            call_command('loaddata', file)
        messages.info(request, f'Database {get_setting("NAME")} has been updated...\n')
    except FileNotFoundError as error:
        messages.error(request, f'Fixture don\'t exist... => Error code: {error}')


def make_archives():
    '''create compressed in zip format archive file with fixtures'''
    if list(Path.iterdir(dest_path)):
        try:
            make_archive(archive_name, 'zip', dest_path)
            print(f'The archive <<{archive_file.name}>> has been packaged...')
        except FileNotFoundError as error:
            print(f'Archiving has failed => Error code: {error}')
    else:
        print(f'Directory {dest_path} is empty...')


def uploadFileFTP(sourceFilePath:Path, destinationDirectory:Path, server:str, username:str, password:str):
    '''sending compressed in zip format archive file with fixtures on ftp server'''
    if check_internet_connection():
        try:
            with FTP(server, username, password) as myFTP:
                print(f'\nConnected to FTP...<<{myFTP.host}>>')
                ftpdirs = list(name for name in myFTP.nlst())

                if destinationDirectory not in ftpdirs:
                    print(f'\nDestination directory <<{destinationDirectory}>> does not exist...\nCreating a target catalog...')
                    try:
                        myFTP.mkd(destinationDirectory)
                        print(f'Destination directory <<{destinationDirectory}>> has been created...')
                        myFTP.cwd(destinationDirectory)
                        if Path.is_file(sourceFilePath):
                            with sourceFilePath.open('rb') as file:
                                myFTP.storbinary(f'STOR {sourceFilePath.name}', file)
                                print(f'\nThe <<{sourceFilePath.name}>> file has been sent to the directory <<{destinationDirectory}>>\n')
                        else:
                            print('\nNo source file...')
                    except ConnectionRefusedError as error:
                        print(f'\nError code: {error}')
                else:
                    try:
                        myFTP.cwd(destinationDirectory)
                        if Path.is_file(sourceFilePath):
                            with sourceFilePath.open('rb') as file:
                                myFTP.storbinary(f'STOR {sourceFilePath.name}', file)
                                print(f'\nFile <<{sourceFilePath.name}>> was sent to the FTP directory <<{destinationDirectory}>>\n')
                    except ConnectionRefusedError as error:
                        print(f'\nError code: {error}')
        except ConnectionRefusedError as error:
            print(f'\nError code: {error}')
    else:
        print(r'No internet connection...')


def getArchiveFilefromFTP(request, server:str, username:str, password:str):
    '''loading compressed in zip format archive file with fixtures on ftp server'''
    if check_internet_connection():
        try:
            with FTP(server, username, password) as myFTP:
                myFTP.cwd(r'/unikolor_db/')
                if Path.is_file(archive_file) and myFTP.size(archive_file.name) != archive_file.stat().st_size:
                    try:
                        archive_file.unlink()
                        myFTP.retrbinary(f'RETR {archive_file.name}', open(archive_file, 'wb').write)
                        messages.info(request, f'\nArchive <<{archive_file.name}>> successfully imported...')
                        unpack_archive(archive_file, dest_path, 'zip')
                        messages.info(request, 'The archive has been unpacked...')
                        readfixture(request)
                    except:
                        messages.error(request, f'File <<{archive_file.name}>> do not exist...')
                elif not Path.is_file(archive_file):
                    try:
                        myFTP.retrbinary(f'RETR {archive_file.name}', open(archive_file, 'wb').write)
                        messages.info(request, f'\nArchive <<{archive_file.name}>> successfully imported...')
                        unpack_archive(archive_file, dest_path, 'zip')
                        messages.info(request, 'The archive has been added and unpacked...')
                        print(f'\n{"*"*22}\nStart read fixtures...\n{"*"*42}')
                        readfixture(request)
                        print(f'{"*"*42}\nFinish read fixtures...\n{"*"*22}\n')
                    except:
                        messages.error(request, f'File <<{archive_file.name}>> do not exist...')
                else:
                    messages.info(request, f'\nDatabase is up to date...')
        except ConnectionError as error:
            messages.error(request, f'Connection error: {error}')
    else:
        messages.error(request, r'No internet connection...')


# serialization json
def export_as_json(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    path = Path(f'backup_json/{opts.verbose_name}.json')
    with path.open('w') as file:
        serialize('json', queryset, indent=4, stream=file)
    messages.success(request, f'Selected records have been serialized to <<{opts.verbose_name}>>')


# archiving of delete records
def archiving_of_deleted_records(worker):
    models = EmployeeData, EmployeeHourlyRate, WorkEvidence, EmployeeLeave, AccountPayment
    all_records = [worker]

    for model in models:
        all_records += list(model.objects.filter(worker=worker))

    path = Path(f'backup_json/erase_worker/{worker.surname}_{worker.forename}.json')
    with path.open('w') as file:
        serialize('json', all_records, indent=4, stream=file)
