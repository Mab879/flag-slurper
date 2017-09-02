import os
from io import BytesIO
from typing import Union

import click
import paramiko

from . import utils
from .config import Config

pass_config = click.make_pass_decorator(Config)


@click.group()
def remote():
    pass


@remote.command()
@click.option('-t', '--team', type=click.INT, default=None)
@click.option('-f', '--flag-id', type=click.INT, default=None)
@click.option('-l', '--location', default=None)
@click.option('-P', '--password', default='cdc', envvar='REMOTE_PASS')
@click.option('-W', '--prompt-password', is_flag=True)
@click.argument('remote')
@pass_config
def plant(conf, team, flag_id, location, password, prompt_password, remote):
    user = conf.user
    utils.check_user(user)

    if not team:
        team = click.prompt('Which team do you want to get flags for?', prompt_suffix='\n> ', default=-1)

    team = None if team < 0 else team
    utils.report_status('Finding flags for team {}'.format(team))

    flags = utils.get_flags(team)
    flags = {i: x for i, x in enumerate(flags)}

    if flag_id is None:
        click.echo('Pick the flag to place')
        for flag_id, flag in flags.items():
            # Admins can see both blue and red flags, tell them which is which
            if user.is_admin:
                click.echo('{}. {} ({})'.format(flag_id, flag['name'], flag['type']))
            else:
                click.echo('{}. {}'.format(flag_id, flag['name']))

        flag = click.prompt('Which Flag', type=click.INT)
    else:
        utils.report_status('Flag supplied from command line')
        flag = flag_id

    if flag not in flags:
        utils.report_error('Invalid selection: {}'.format(flags))
        exit(1)
    flag = flags[flag]
    data = flag['data']
    filename = flag['filename']

    if not location:
        location = click.prompt('Enter the remote location', default='/root')
    else:
        utils.report_status('Location supplied from command line')
    location = os.path.join(location, filename)

    # Remote Section
    if prompt_password:
        password = click.prompt('Remote Password', hide_input=True)
    username, host, port = utils.parse_remote(remote)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password, port=port)

    pkt = BytesIO()
    pkt.write(data.encode('utf-8'))
    pkt.write(b'\n')
    pkt.seek(0)

    sftp = ssh.open_sftp()
    sftp.putfo(pkt, location)
    utils.report_status('Verifying flag plant')

    planted_contents = get_file_contents(ssh, location)

    if planted_contents != data:
        utils.report_warning('Planted flag data does not match, double check the plant')
    else:
        utils.report_success('Flag Planted')


@remote.command()
@click.option('-t', '--team', help='Team number', default=None, prompt=True)
@click.option('-f', '--flag', help='Flag Slug', default=None, prompt=True)
@click.option('-l', '--location', default=None, prompt=True)
@click.option('-P', '--password', default='cdc', envvar='REMOTE_PASS')
@click.option('-W', '--prompt_password', is_flag=True)
@click.option('-s', '--search', help='Force search for flag', is_flag=True)
@click.argument('remote')
@pass_config
def capture(conf, team, flag, location, password, prompt_password, remote, search):
    user = conf.user
    utils.check_user(user)

    filename = 'team{}_{}.flag'.format(team, flag)
    base_dir = location
    location = os.path.join(location, filename)
    search_glob = os.path.join(base_dir, '*flag*')

    if prompt_password:
        password = click.prompt('Remote Pasword', hide_input=True)
    username, host, port = utils.parse_remote(remote)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password, port=port)

    planted = get_file_contents(ssh, location)
    if not planted or search:
        _, stdout, stderr = ssh.exec_command('ls {}'.format(search_glob))

        files = []
        for line in stdout.read().splitlines():
            files.append(line.decode('utf-8'))

        print("Found possible flags:", ', '.join(files))
        for file in files:
            utils.report_status('Checking possible flag: {}'.format(file))
            contents = get_file_contents(ssh, file)
            if not contents:
                utils.report_warning('File {} does not contain flag'.format(file))
            elif 10 < len(contents) < 60:
                utils.report_success('Possible Flag {}: {}'.format(file, contents))
            else:
                utils.report_warning('File {} incorrect size for flag'.format(file))
    else:
        utils.report_success('Found Flag: {}'.format(planted))


def get_file_contents(ssh: paramiko.SSHClient, file: str) -> Union[str, bool]:
    _, stdout, stderr = ssh.exec_command('cat {}'.format(file))
    err = stderr.read()
    if len(err) > 0:
        return False

    return stdout.read().strip().decode('utf-8')
