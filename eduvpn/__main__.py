import logging
from sys import exit
from pathlib import Path
from typing import Optional
from requests_oauthlib import OAuth2Session
from eduvpn.menu import menu, profile_choice, write_to_nm_choice
from eduvpn.nm import save_connection
from eduvpn.oauth2 import get_oauth
from eduvpn.remote import get_info, list_profiles, get_config, create_keypair, list_orgs, list_institutes
from eduvpn.settings import CLIENT_ID, ORGANISATION_URI, Ed25519_PUBLIC_KEY, INSTITUTES_URI
from eduvpn.storage import get_entry, set_entry, write_config
from eduvpn.crypto import make_verifier
import argparse


def parse_args() -> Optional[str]:
    parser = argparse.ArgumentParser(description='The eduVPN command line client')
    parser.add_argument('search', metavar='search', type=str, nargs='?', help='A URL or search term')
    args = parser.parse_args()
    return args.search


def main():
    logging.basicConfig(level=logging.INFO)
    search_term = parse_args()

    verifier = make_verifier(Ed25519_PUBLIC_KEY)

    if isinstance(search_term, str) and search_term.lower().startswith('https://'):
        base_url = search_term
    else:
        institutes = list_institutes(INSTITUTES_URI, verifier=verifier)
        orgs = list_orgs(ORGANISATION_URI, verifier=verifier)
        base_url = menu(institutes=institutes, orgs=orgs, search_term=search_term)

    if not base_url:
        exit(1)

    exists = get_entry(base_url)

    if exists:
        token, api_base_uri, token_endpoint, authorization_endpoint = exists
        oauth = OAuth2Session(client_id=CLIENT_ID, token=token, auto_refresh_url=token_endpoint)
    else:
        api_base_uri, token_endpoint, auth_endpoint = get_info(base_url)
        oauth = get_oauth(token_endpoint, auth_endpoint)
        set_entry(base_url, oauth.token, api_base_uri, token_endpoint, auth_endpoint)

    oauth.refresh_token(token_url=token_endpoint)
    profiles = list_profiles(oauth, api_base_uri)
    profile_id = profile_choice(profiles)
    config = get_config(oauth, api_base_uri, profile_id)
    private_key, certificate = create_keypair(oauth, api_base_uri)

    if write_to_nm_choice():
        save_connection(config, private_key, certificate)
    else:
        target = Path('eduVPN.ovpn').resolve()
        print(f"Writing configuration to {target}")
        write_config(config, private_key, certificate, target)


if __name__ == '__main__':
    main()
