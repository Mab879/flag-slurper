import click
import pathlib

from . import __version__
from . import utils
from .config import Config
from .project import Project

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}

pass_conf = click.make_pass_decorator(Config)


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('-c', '--config', type=click.Path(), envvar='CONFIG_FILE')
@click.option('--iscore-url', envvar='ISCORE_URL', default=None)
@click.option('--api-token', envvar='ISCORE_API_TOKEN', default=None)
@click.option('-p', '--project', envvar='SLURPER_PROJECT', type=click.Path(), default=None)
@click.option('-np', '--no-project', is_flag=True)
@click.option('-d', '--debug', is_flag=True)
@click.version_option(version=__version__, prog_name='flag-slurper')
@click.pass_context
def cli(ctx, config, iscore_url, api_token, project, debug, no_project):
    ctx.obj = Config.load(config)
    ctx.obj.cond_set('iscore', 'url', iscore_url)
    ctx.obj.cond_set('iscore', 'api_token', api_token)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    if project and not no_project:
        project = pathlib.Path(project)
        project = project.expanduser()
        if project.is_dir():
            project = project / 'project.yml'
        p = Project.get_instance()
        p.load(str(project))

    if debug:  # pragma: no cover
        import logging
        logger = logging.getLogger("peewee")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

        logger = logging.getLogger('flag_slurper')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())


@cli.command()
@click.option('-t', '--team', type=click.INT, default=None)
@pass_conf
def plant(conf, team):
    user = conf.user
    utils.check_user(user)

    if not team:
        team = click.prompt('Which team do you want to get flags for?', prompt_suffix='\n> ', default=-1)

    team = None if team < 0 else team
    click.echo('Team: {}'.format(team))

    flags = utils.get_flags(team)
    flags = {i: x for i, x in enumerate(flags)}

    click.echo('Pick the flag to place')
    for flag_id, flag in flags.items():
        # Admins can see both blue and red flags, tell them which is which
        if user.is_admin:
            click.echo('{}. {} ({})'.format(flag_id, flag['name'], flag['type']))
        else:
            click.echo('{}. {}'.format(flag_id, flag['name']))

    flag = click.prompt('Which Flag', type=click.INT)
    if flag not in flags:
        utils.report_error('Invalid selection: {}'.format(flag))
        exit(1)
    flag = flags[flag]
    click.echo('Flag: {}'.format(flag['data']))


# Load additional commands
from .credentials import creds
from .project import project
cli.add_command(creds)
cli.add_command(project)

# Feature detect remote functionality
try:
    import paramiko  # noqa
    from .remote import remote
    from .autopwn import autopwn
    cli.add_command(remote)
    cli.add_command(autopwn)
except ImportError:  # pragma: no cover
    pass
