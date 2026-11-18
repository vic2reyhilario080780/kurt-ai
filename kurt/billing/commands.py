"""Personal wallet commands. Manual credit/settlement are local operator actions only."""
import json
import os
from pathlib import Path
import time

from .ledger import Wallet, units
from .gateway import Gateway, ORIGINS, KEY_VARS, CLI_PROVIDERS
from .payments import Payments
from .app import BillingApp
from . import WalletError


def default_config():
    return {'currency':'USD','markup_percent':0,'payment_return_url':'','cli_session_budget_usd':'5',
        'providers':{p:{'models':['*'],'reserve_usd':'25' if p in ('fal','replicate') else '1',
                        'max_output_tokens':8192} for p in ORIGINS},
        'cli_profiles':{'copilot':{'provider':'openrouter','model':'openai/gpt-oss-120b'},
                        'vibe':{'provider':'mistral','model':'mistral-vibe-cli-latest','alias':'mistral-medium-3.5'},
                        'openclaw':{'provider':'groq','model':'openai/gpt-oss-20b'},
                        'deepseek':{'provider':'deepseek','model':'deepseek-flash'},
                        'deepseek-cli':{'provider':'deepseek','model':'deepseek-flash'}}}


def initialize(root):
    root=Path(root).expanduser().resolve()
    if root.exists() and any(root.iterdir()): raise ValueError('Use a new empty private wallet directory.')
    wallet=Wallet(root)
    from kurt.utils.security import write_private_text
    tenant,token=wallet.grant('pro',days=366)
    write_private_text(root/'owner.kurt-token',token+'\n')
    write_private_text(root/'owner.json',json.dumps({'tenant':tenant},indent=2)+'\n')
    write_private_text(root/'wallet-config.json',json.dumps(default_config(),indent=2)+'\n')
    return {'state_dir':str(root),'tenant':tenant,'currency':'USD','markup_percent':0,'balance_usd':'0',
            'token_file':str(root/'owner.kurt-token'),'payments_enabled':False}


def owner(root):
    root=Path(root).expanduser().resolve()
    return Wallet(root),json.loads((root/'owner.json').read_text())['tenant']


def connect(url,token_file):
    from .client import Client, read_token
    from kurt.core.persona import save_persona
    token=read_token(token_file)
    result=Client(url,token).request('/wallet/status')
    save_persona({'wallet_enabled':True,'wallet_url':url.rstrip('/'),'wallet_token_file':str(Path(token_file).expanduser().resolve())})
    return result


def slash(args):
    from .client import from_env
    parts=args.split()
    if not parts or parts==['status']: return from_env().request('/wallet/status')
    if parts==['history']: return from_env().request('/wallet/history')
    if parts==['catalog']: return from_env().request('/wallet/catalog')
    if len(parts)==2 and parts[0]=='topup':
        value=units(parts[1])
        if value%(10**10): raise ValueError('Top-ups use whole USD cents.')
        return from_env().request('/wallet/topups',{'amount_cents':value//10**10})
    if len(parts)==2 and parts[0]=='reconcile': return from_env().request('/wallet/reconcile',{'request_id':parts[1]})
    raise ValueError('Use /wallet status | history | catalog | topup <USD> | reconcile <request-id>.')


def register_commands(app):
    import typer
    commands=typer.Typer(help='Central USD wallet: actual provider costs, zero markup. Manual credits are not purchases.')
    app.add_typer(commands,name='wallet')
    def emit(callback):
        try: typer.echo(json.dumps(callback(),ensure_ascii=False,indent=2))
        except (ValueError,OSError,RuntimeError) as exc:
            typer.echo(str(exc),err=True); raise typer.Exit(1)
    @commands.callback(invoke_without_command=True)
    def callback(ctx:typer.Context):
        if ctx.invoked_subcommand is None: emit(lambda:slash('status'))
    @commands.command('status')
    def status(): emit(lambda:slash('status'))
    @commands.command('history')
    def history(): emit(lambda:slash('history'))
    @commands.command('catalog')
    def catalog(): emit(lambda:slash('catalog'))
    @commands.command('topup')
    def topup(amount_usd:str):
        """Create a payment checkout; balance changes only after a verified paid webhook."""
        emit(lambda:slash('topup '+amount_usd))
    @commands.command('reconcile')
    def reconcile(request_id:str): emit(lambda:slash('reconcile '+request_id))
    @commands.command('init')
    def init(state_dir:Path=typer.Option(...,'--state-dir')):
        """Create private personal state with ZERO balance; does not purchase credits."""
        emit(lambda:initialize(state_dir))
    @commands.command('connect')
    def connect_cmd(url:str,token_file:Path=typer.Option(...,'--token-file')):
        """Verify your wallet then enable it for native AI and supported CLI sessions."""
        emit(lambda:connect(url,token_file))
    @commands.command('off')
    def off():
        from kurt.core.persona import save_persona
        if os.environ.get('KURT_WALLET_MODE')=='1':
            raise typer.BadParameter('Unset KURT_WALLET_MODE=1 to turn off an environment-managed wallet.')
        save_persona({'wallet_enabled':False}); typer.echo('Wallet routing disabled. Saved provider setup remains available.')
    @commands.command('credit')
    def credit(amount_usd:str,state_dir:Path=typer.Option(...,'--state-dir'),
               reference:str=typer.Option(...,'--reference'),reason:str=typer.Option(...,'--reason')):
        """LOCAL OPERATOR ONLY: manual funded-account credit, not a verified payment."""
        def apply():
            store,tenant=owner(state_dir); store.manual_credit(tenant,amount_usd,reference,reason)
            return {'source':'manual_operator_credit','verified_payment':False,**store.summary(tenant)}
        emit(apply)
    @commands.command('settle')
    def settle(request_id:str,actual_usd:str,state_dir:Path=typer.Option(...,'--state-dir'),
               evidence:str=typer.Option(...,'--evidence')):
        """LOCAL OPERATOR ONLY: settle a pending request against an actual provider bill."""
        def apply():
            store,tenant=owner(state_dir)
            store.settle(tenant,request_id,actual_usd,basis='operator_verified_provider_bill',evidence=evidence)
            return store.summary(tenant)
        emit(apply)
    @commands.command('correct')
    def correct(request_id:str,actual_usd:str,state_dir:Path=typer.Option(...,'--state-dir'),
                evidence:str=typer.Option(...,'--evidence')):
        """LOCAL OPERATOR ONLY: append an invoice correction to an already settled cost."""
        def apply():
            store,tenant=owner(state_dir);store.correct(tenant,request_id,actual_usd,evidence=evidence)
            return store.summary(tenant)
        emit(apply)
    @commands.command('serve')
    def serve(state_dir:Path=typer.Option(...,'--state-dir'),personal:bool=typer.Option(False,'--personal'),
              host:str=typer.Option('127.0.0.1','--host'),port:int=typer.Option(8098,'--port')):
        """Run the gateway. Personal mode reads Kurt setup keys inside this server only."""
        if host not in ('127.0.0.1','::1','localhost'): raise typer.BadParameter('Use loopback here; use the HTTPS factory deployment for remote access.')
        import uvicorn
        root=state_dir.expanduser().resolve(); config=json.loads((root/'wallet-config.json').read_text())
        if personal:
            from dotenv import dotenv_values
            from kurt.utils.env_loader import ENV_PATH
            saved=dotenv_values(ENV_PATH,interpolate=False) if ENV_PATH.exists() else {}
            keys={p:saved.get(name,'') for p,name in KEY_VARS.items()}
            keys['google']=keys.get('google') or saved.get('GEMINI_API_KEY') or saved.get('GOOGLE_API_KEY','')
            keys['fal_billing']=saved.get('FAL_BILLING_KEY','')
        else: keys={p:os.environ.get('KURT_WALLET_'+name,'') for p,name in KEY_VARS.items()}
        store=Wallet(root); gateway=Gateway(store,config,keys)
        payments=Payments(store,os.environ.get('KURT_WALLET_STRIPE_KEY',''),os.environ.get('KURT_WALLET_STRIPE_WEBHOOK_SECRET',''),
                          live=os.environ.get('KURT_WALLET_STRIPE_LIVE')=='1',return_url=config.get('payment_return_url',''))
        uvicorn.run(BillingApp(store,gateway,payments,require_https=False),host=host,port=port,access_log=False)
