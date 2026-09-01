import tempfile
from fastapi.testclient import TestClient
from main import app
from app.core import config
from app.services.dossier_service import create_dossier, dossier_root, create_section_document, write_generated, _safe_dir_name
import asyncio

# Set temporary DOSSIERS_ROOT
tmp = tempfile.mkdtemp()
config.settings.DOSSIERS_ROOT = tmp

client = TestClient(app)

# Create dossier
summary = create_dossier('test')
root = dossier_root(summary['id'])
section = create_section_document(root=root, ctd_path='3.2.P.8.1', title='Stability', module='Module 3 — Quality', stem='section1')
write_generated(section['section_dir'], section['stem'], 'original content')

safe_module = _safe_dir_name('Module 3 — Quality')
safe_section = _safe_dir_name('3.2.P.8.1 Stability')
payload = {'target_language':'fr','section_path':f'{safe_module}/{safe_section}','stem':'section1'}
resp = client.post(f"/api/v1/dossiers/{summary['id']}/translate/", json=payload)
print('POST resp', resp.status_code, resp.json())
# List files
import os
print('Files in section_dir:', os.listdir(section['section_dir']))
status_resp = client.get(f"/api/v1/dossiers/{summary['id']}/translate/status", params={'section_path':f'{safe_module}/{safe_section}'})
print('GET status', status_resp.status_code, status_resp.json())
