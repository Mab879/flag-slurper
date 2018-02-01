from unittest import mock

import pytest

from flag_slurper.config import Config
from flag_slurper.models import User


def test_config_singleton(config):
    assert config is Config.get_instance()


def test_config_creation():
    Config.instance = None
    config = Config.get_instance()
    assert Config.instance is config


def test_config_load_extra(tmpdir):
    rc = tmpdir.join("flagrc.ini")
    rc.write("[iscore]\nurl=TESTURL\n")

    conf = Config.load(str(rc), noflagrc=True)
    assert conf['iscore']['url'] == 'TESTURL'


def test_config_cond_set(config):
    config.cond_set('iscore', 'api_token', 'TESTOKEN')
    assert config['iscore']['api_token'] == 'TESTOKEN'


def test_config_api_url(config):
    assert config.api_url == 'https://iscore.iseage.org/api/v1'


@mock.patch.object(Config, 'prompt_creds', lambda self: True)
def test_config_request_extras_token(config):
    config.cond_set('iscore', 'api_token', 'TESTOKEN')
    extras = config.request_extras()
    assert 'headers' in extras and 'Authorization' in extras['headers']
    assert extras['headers']['Authorization'] == 'Token TESTOKEN'


@mock.patch.object(Config, 'prompt_creds', lambda self: True)
def test_config_request_extras_creds(config):
    config.credentials = ('testuser', 'testpass')
    extras = config.request_extras()
    assert 'auth' in extras
    assert extras['auth'] == ('testuser', 'testpass')


def test_config_user(config):
    with mock.patch('flag_slurper.utils.get_user') as get_user:
        user = User({
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'test',
            'is_superuser': True,
            'profile': {'is_red': False},
        })
        get_user.return_value = user
        result = config.user
        assert result == user


@pytest.mark.skip("Can't mock input")
def test_config_prompt_token(config, capsys):
    with mock.patch.object(__builtins__, 'input') as input:
        input.return_value = "API_TOKEN"
        config.prompt_creds()
        captured = capsys.readouterr()
        assert captured.out == "Enter your IScorE API Token (leave blank to use your credentials)\n"
        assert config['iscore']['api_token'] == 'API_TOKEN'
