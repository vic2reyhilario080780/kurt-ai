import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core import credential_transfer as transfer
from kurt.utils import env_loader

PASSWORD = 'fixture-only-passphrase-2026'


class CredentialTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.env=self.root/'source.env'
        self.env.write_text('OPENAI_API_KEY="synthetic-provider-key"\nCUSTOM_ENDPOINT="https://example.invalid"\nMULTILINE="first\\nsecond"\n')
        self.target=self.root/'owner.kurt-credentials'
        context=patch.object(env_loader,'ENV_PATH',self.env);context.start();self.addCleanup(context.stop)

    def test_encrypted_roundtrip_contains_no_plaintext_and_no_keys_in_result(self):
        report=transfer.export_credentials(self.target,PASSWORD)
        self.assertNotIn(b'synthetic-provider-key',self.target.read_bytes())
        self.assertNotIn(b'OPENAI_API_KEY',self.target.read_bytes())
        self.assertNotIn('synthetic-provider-key',json.dumps(report))
        imported=self.root/'new-home/.kurt/.env'
        with patch.object(env_loader,'ENV_PATH',imported):
            result=transfer.import_credentials(self.target,PASSWORD)
        from dotenv import dotenv_values
        values=dotenv_values(imported,interpolate=False)
        self.assertEqual(values['OPENAI_API_KEY'],'synthetic-provider-key')
        self.assertEqual(values['MULTILINE'],'first\nsecond')
        self.assertEqual(result['imported_variables'],3)

    def test_wrong_password_and_tampering_never_write_target(self):
        transfer.export_credentials(self.target,PASSWORD)
        original=self.env.read_bytes()
        with self.assertRaisesRegex(ValueError,'Incorrect passphrase'):
            transfer.import_credentials(self.target,'different-passphrase-2026')
        self.assertEqual(self.env.read_bytes(),original)
        data=bytearray(self.target.read_bytes());data[-10]^=1;self.target.write_bytes(data)
        with self.assertRaises(ValueError):transfer.import_credentials(self.target,PASSWORD)
        self.assertEqual(self.env.read_bytes(),original)

    def test_existing_keys_preserved_unless_replace_is_explicit(self):
        transfer.export_credentials(self.target,PASSWORD)
        self.env.write_text('OPENAI_API_KEY="existing-device-key"\nEXISTING_ONLY="keep"\n')
        result=transfer.import_credentials(self.target,PASSWORD)
        from dotenv import dotenv_values
        self.assertEqual(dotenv_values(self.env)['OPENAI_API_KEY'],'existing-device-key')
        self.assertEqual(result['existing_variables_preserved'],1)
        transfer.import_credentials(self.target,PASSWORD,replace=True)
        values=dotenv_values(self.env)
        self.assertEqual(values['OPENAI_API_KEY'],'synthetic-provider-key')
        self.assertEqual(values['EXISTING_ONLY'],'keep')

    def test_exports_randomized_and_existing_export_is_not_overwritten(self):
        transfer.export_credentials(self.target,PASSWORD)
        other=self.root/'other.kurt-credentials';transfer.export_credentials(other,PASSWORD)
        self.assertNotEqual(self.target.read_bytes(),other.read_bytes())
        original=self.target.read_bytes()
        with self.assertRaises(FileExistsError):transfer.export_credentials(self.target,PASSWORD)
        self.assertEqual(self.target.read_bytes(),original)

    def test_short_password_and_bad_source_fail_without_export(self):
        with self.assertRaises(ValueError):transfer.export_credentials(self.target,'short')
        self.assertFalse(self.target.exists())
        for raw in [b'KEY="unterminated',b'KEY=a\nKEY=b\n',b'KEY\n',b'KEY=bad\x00value',b'x'*(transfer.MAX_ENV+1)]:
            self.env.write_bytes(raw)
            with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):transfer.export_credentials(self.target,PASSWORD)
            self.assertFalse(self.target.exists())

    def test_invalid_header_and_oversize_do_not_attempt_kdf(self):
        for raw in [b'not encrypted',b'x'*(transfer.MAX_FILE+1)]:
            self.target.write_bytes(raw)
            with patch.object(transfer,'_cipher') as cipher,self.assertRaises(ValueError):
                transfer.import_credentials(self.target,PASSWORD)
            cipher.assert_not_called()

    def test_placeholder_target_is_replaced_and_dollar_references_not_expanded(self):
        self.env.write_text('OPENAI_API_KEY="synthetic-provider-key"\nREFERENCE="${HOME}/literal"\n')
        transfer.export_credentials(self.target,PASSWORD)
        self.env.write_text('OPENAI_API_KEY=sk-your-key-here\n')
        transfer.import_credentials(self.target,PASSWORD)
        from dotenv import dotenv_values
        values=dotenv_values(self.env,interpolate=False)
        self.assertEqual(values['REFERENCE'],'${HOME}/literal')
        self.assertEqual(values['OPENAI_API_KEY'],'synthetic-provider-key')

    def test_installer_checks_transfer_before_install_and_keeps_password_out_of_arguments(self):
        import bootstrap
        args=type('Args',(),{'features':'web','cli_tools':False,'browser':False,'dry_run':True,
                             'credentials_file':str(self.target)})()
        with patch.object(bootstrap.subprocess,'run') as run, self.assertRaises(ValueError):
            bootstrap.install(args)
        run.assert_not_called()
        transfer.export_credentials(self.target,PASSWORD)
        with patch('builtins.print') as output:
            bootstrap.install(args)
        plan=json.loads(output.call_args.args[0])
        self.assertIn('migration',plan['features'])
        self.assertNotIn(PASSWORD,json.dumps(plan))
