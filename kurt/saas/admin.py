"""Local operator commands; no public admin/plan-upgrade HTTP endpoints."""
import argparse
import os
from pathlib import Path
from .store import Store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',required=True,type=Path)
    commands=parser.add_subparsers(dest='command',required=True)
    grant=commands.add_parser('grant')
    grant.add_argument('--plan',choices=('starter','pro'),required=True)
    grant.add_argument('--tenant')
    grant.add_argument('--days',type=int,default=30)
    grant.add_argument('--token-file',type=Path,required=True)
    revoke=commands.add_parser('revoke')
    revoke.add_argument('tenant')
    args=parser.parse_args()
    store=Store(args.state_dir)
    if args.command == 'revoke':
        store.revoke(args.tenant)
        print('Tenant device tokens revoked.'); return
    if not str(args.token_file).endswith(".kurt-token"):
        parser.error("Use a .kurt-token filename so credential file guards recognize it")
    # Only a fresh private file receives the token; never stdout or shell history.
    fd=os.open(args.token_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        tenant,token=store.grant(args.plan,args.days,args.tenant)
        with os.fdopen(fd,'w') as stream:
            stream.write(token+'\n')
    except BaseException:
        try: os.close(fd)
        except OSError: pass
        args.token_file.unlink(missing_ok=True)
        raise
    print(f'Tenant: {tenant}\nDevice token saved to private file: {args.token_file}')


if __name__ == '__main__':
    main()
