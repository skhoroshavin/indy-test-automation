import pytest
import asyncio
from system.utils import *

import logging
logger = logging.getLogger(__name__)


@pytest.mark.usefixtures('docker_setup_and_teardown')
class TestEndorserSuite:

    @pytest.mark.parametrize('role', ['TRUSTEE', 'STEWARD', 'ENDORSER'])
    @pytest.mark.asyncio
    async def test_case_endorser_roles(
            self, pool_handler, wallet_handler, get_default_trustee, role
    ):
        # acceptable roles are ENDORSER, STEWARD, TRUSTEE
        trustee_did, _ = get_default_trustee
        test_did, test_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        none_did, none_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        e_did, e_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        res = await send_nym(pool_handler, wallet_handler, trustee_did, none_did, none_vk, 'No role', None)
        assert res['op'] == 'REPLY'
        res = await send_nym(pool_handler, wallet_handler, trustee_did, e_did, e_vk, 'Endorser', role)
        assert res['op'] == 'REPLY'

        # negative case - build txn with endorser, append none role did as endorser, multisign with both
        req0 = await ledger.build_nym_request(e_did, test_did, test_vk, 'Alias', None)
        req0 = await ledger.append_request_endorser(req0, none_did)
        req0 = await ledger.multi_sign_request(wallet_handler, e_did, req0)
        req0 = await ledger.multi_sign_request(wallet_handler, none_did, req0)
        res0 = json.loads(await ledger.submit_request(pool_handler, req0))
        print(res0)
        assert res0['op'] == 'REJECT'

        # positive case - build txn with none role did, append endorser as endorser, multisign with both
        req1 = await ledger.build_nym_request(none_did, test_did, test_vk, 'Alias', None)
        req1 = await ledger.append_request_endorser(req1, e_did)
        req1 = await ledger.multi_sign_request(wallet_handler, none_did, req1)
        req1 = await ledger.multi_sign_request(wallet_handler, e_did, req1)
        res1 = json.loads(await ledger.submit_request(pool_handler, req1))
        print(res1)
        assert res1['op'] == 'REPLY'

    @pytest.mark.asyncio
    async def test_case_endorser_specification(
            self, pool_handler, wallet_handler, get_default_trustee
    ):
        pass

    @pytest.mark.asyncio
    async def test_case_happy_path(
            self, pool_handler, wallet_handler, get_default_trustee
    ):
        trustee_did, _ = get_default_trustee
        off_did, off_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        e_did, e_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        test_did, test_vk = await did.create_and_store_my_did(wallet_handler, '{}')
        res = await send_nym(pool_handler, wallet_handler, trustee_did, off_did, off_vk, 'No role', None)
        assert res['op'] == 'REPLY'
        res = await send_nym(pool_handler, wallet_handler, trustee_did, e_did, e_vk, 'Endorser', 'ENDORSER')
        assert res['op'] == 'REPLY'

        # try to add new did by none role did - should fail
        req = await ledger.build_nym_request(off_did, test_did, test_vk, 'Alias 1', None)
        res = json.loads(await ledger.sign_and_submit_request(pool_handler, wallet_handler, off_did, req))
        assert res['op'] == 'REJECT'
        # add new did using none role did as builder and endorser did as endorser
        req0 = await ledger.build_nym_request(off_did, test_did, test_vk, 'Alias 1', None)
        req0 = await ledger.append_request_endorser(req0, e_did)
        req0 = await ledger.multi_sign_request(wallet_handler, off_did, req0)
        req0 = await ledger.multi_sign_request(wallet_handler, e_did, req0)
        res0 = json.loads(await ledger.submit_request(pool_handler, req0))
        print(res0)
        assert res0['op'] == 'REPLY'

        schema_id, schema_json = await anoncreds.issuer_create_schema(
            off_did, 'Schema 1', '0.1', json.dumps(['a1', 'a2'])
        )
        # try to add new schema by none role did - should fail
        req = await ledger.build_schema_request(off_did, schema_json)
        res = json.loads(await ledger.sign_and_submit_request(pool_handler, wallet_handler, off_did, req))
        assert res['op'] == 'REJECT'
        # add new schema using none role did as builder and endorser did as endorser
        req1 = await ledger.build_schema_request(off_did, schema_json)
        req1 = await ledger.append_request_endorser(req1, e_did)
        req1 = await ledger.multi_sign_request(wallet_handler, off_did, req1)
        req1 = await ledger.multi_sign_request(wallet_handler, e_did, req1)
        res1 = json.loads(await ledger.submit_request(pool_handler, req1))
        print(res1)
        assert res1['op'] == 'REPLY'

        await asyncio.sleep(1)
        res = json.dumps(await get_schema(pool_handler, wallet_handler, trustee_did, schema_id))
        schema_id, schema_json = await ledger.parse_get_schema_response(res)
        cred_def_id, cred_def_json = await anoncreds.issuer_create_and_store_credential_def(
            wallet_handler, off_did, schema_json, 'cred def tag', None, json.dumps({'support_revocation': True})
        )
        # try to add new cred def by none role did - should fail
        req = await ledger.build_cred_def_request(off_did, cred_def_json)
        res = json.loads(await ledger.sign_and_submit_request(pool_handler, wallet_handler, off_did, req))
        assert res['op'] == 'REJECT'
        # add new cred def using none role did as builder and endorser did as endorser
        req2 = await ledger.build_cred_def_request(off_did, cred_def_json)
        req2 = await ledger.append_request_endorser(req2, e_did)
        req2 = await ledger.multi_sign_request(wallet_handler, off_did, req2)
        req2 = await ledger.multi_sign_request(wallet_handler, e_did, req2)
        res2 = json.loads(await ledger.submit_request(pool_handler, req2))
        print(res2)
        assert res2['op'] == 'REPLY'

        tails_writer_config = json.dumps({'base_dir': 'tails', 'uri_pattern': ''})
        tails_writer_handle = await blob_storage.open_writer('default', tails_writer_config)
        revoc_reg_id, revoc_reg_def_json, revoc_reg_entry_json = await anoncreds.issuer_create_and_store_revoc_reg(
            wallet_handler, off_did, None, 'revoc reg tag', cred_def_id, json.dumps(
                {'max_cred_num': 100, 'issuance_type': 'ISSUANCE_BY_DEFAULT'}
            ), tails_writer_handle
        )
        # try to add new revoc reg def by none role did - should fail
        req = await ledger.build_revoc_reg_def_request(off_did, revoc_reg_def_json)
        res = json.loads(await ledger.sign_and_submit_request(pool_handler, wallet_handler, off_did, req))
        assert res['op'] == 'REJECT'
        # add new revoc reg def using none role did as builder and endorser did as endorser
        req3 = await ledger.build_revoc_reg_def_request(off_did, revoc_reg_def_json)
        req3 = await ledger.append_request_endorser(req3, e_did)
        req3 = await ledger.multi_sign_request(wallet_handler, off_did, req3)
        req3 = await ledger.multi_sign_request(wallet_handler, e_did, req3)
        res3 = json.loads(await ledger.submit_request(pool_handler, req3))
        print(res3)
        assert res3['op'] == 'REPLY'

        # try to add new revoc reg entry by none role did - should fail
        req = await ledger.build_revoc_reg_entry_request(off_did, revoc_reg_id, 'CL_ACCUM', revoc_reg_entry_json)
        res = json.loads(await ledger.sign_and_submit_request(pool_handler, wallet_handler, off_did, req))
        assert res['op'] == 'REJECT'
        # add new revoc reg entry using none role did as builder and endorser did as endorser
        req4 = await ledger.build_revoc_reg_entry_request(off_did, revoc_reg_id, 'CL_ACCUM', revoc_reg_entry_json)
        req4 = await ledger.append_request_endorser(req4, e_did)
        req4 = await ledger.multi_sign_request(wallet_handler, off_did, req4)
        req4 = await ledger.multi_sign_request(wallet_handler, e_did, req4)
        res4 = json.loads(await ledger.submit_request(pool_handler, req4))
        print(res4)
        assert res4['op'] == 'REPLY'
