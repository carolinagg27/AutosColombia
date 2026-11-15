"""Verificaciones de estructura, enlaces de plantillas y JavaScript."""
import ast
from pathlib import Path
import re
import shutil
import subprocess

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'app/templates'


def _rutas_definidas():
    rutas = {'static', 'inicio'}
    for archivo in (ROOT / 'app/routes').glob('*.py'):
        if archivo.name == '__init__.py':
            continue
        arbol = ast.parse(archivo.read_text(encoding='utf-8'))
        for nodo in arbol.body:
            if isinstance(nodo,(ast.FunctionDef,ast.AsyncFunctionDef)):
                for decorador in nodo.decorator_list:
                    if (isinstance(decorador,ast.Call) and
                        isinstance(decorador.func,ast.Attribute) and
                        isinstance(decorador.func.value,ast.Name) and
                        decorador.func.value.id=='bp' and
                        decorador.func.attr in ('route','get','post')):
                        rutas.add(archivo.stem+'.'+nodo.name)
    return rutas


def test_todas_las_plantillas_compilan():
    entorno = Environment(loader=FileSystemLoader(TEMPLATES))
    entorno.filters['cop'] = lambda valor: valor
    for archivo in TEMPLATES.glob('*.html'):
        assert entorno.get_template(archivo.name) is not None,archivo.name


def test_enlaces_url_for_apuntan_a_rutas_reales():
    rutas = _rutas_definidas()
    for archivo in TEMPLATES.glob('*.html'):
        texto = archivo.read_text(encoding='utf-8')
        enlaces = re.findall(r'''url_for\(\s*['\"]([\w.]+)['\"]''',texto)
        assert set(enlaces).issubset(rutas), (archivo.name, sorted(set(enlaces)-rutas))


def test_todos_los_formularios_post_contienen_csrf():
    # Se buscan fragmentos entre <form ...> y </form>; no se duplican elementos.
    for archivo in TEMPLATES.glob('*.html'):
        texto=archivo.read_text(encoding='utf-8')
        formularios = re.findall(r'<form\b[^>]*>.*?</form>',texto,flags=re.S|re.I)
        for formulario in formularios:
            etiqueta=re.match(r'<form\b[^>]*>',formulario,flags=re.S|re.I).group(0)
            if re.search(r'method=["\']post["\']',etiqueta,flags=re.I):
                assert 'csrf_token' in formulario,archivo.name


def test_python_sin_errores_de_sintaxis():
    for archivo in ROOT.rglob('*.py'):
        if '.venv' in archivo.parts: continue
        ast.parse(archivo.read_text(encoding='utf-8'),filename=str(archivo))


def test_javascript_sintaxis_valida():
    if shutil.which('node') is None:
        pytest.skip('Node no está disponible; revisar sintaxis en Windows')
    for archivo in (ROOT/'app/static/js').glob('*.js'):
        respuesta=subprocess.run(['node','--check',str(archivo)],capture_output=True,text=True)
        assert respuesta.returncode==0,respuesta.stderr


def test_zona_horaria_disponible_en_instalacion_windows():
    requisitos=(ROOT/'requirements.txt').read_text(encoding='utf-8')
    assert 'tzdata' in requisitos and 'win32' in requisitos
