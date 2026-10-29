"""Diagnóstico somente leitura: não instala, baixa nem inicia serviços."""

import argparse
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def consultar(comando):
    """Limita tempo e saída sem usar shell ou exibir variáveis de ambiente."""
    try:
        resultado = subprocess.run(
            comando, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=8, check=False,
        )
        return {"codigo": resultado.returncode, "saida": resultado.stdout.strip()[:12000]}
    except (OSError, subprocess.TimeoutExpired) as erro:
        return {"codigo": None, "erro": type(erro).__name__}


def memoria_total():
    """Consulta RAM física sem instalar bibliotecas."""
    if os.name == "nt":
        class EstadoMemoria(ctypes.Structure):
            _fields_ = [
                ("tamanho", ctypes.c_ulong), ("uso", ctypes.c_ulong),
                ("fisica", ctypes.c_ulonglong), ("livre", ctypes.c_ulonglong),
                ("pagina", ctypes.c_ulonglong), ("pagina_livre", ctypes.c_ulonglong),
                ("virtual", ctypes.c_ulonglong), ("virtual_livre", ctypes.c_ulonglong),
                ("estendida", ctypes.c_ulonglong),
            ]
        estado = EstadoMemoria()
        estado.tamanho = ctypes.sizeof(estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            return estado.fisica
    elif hasattr(os, "sysconf"):
        try:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (OSError, ValueError):
            pass
    return None


def diagnosticar(projeto):
    """Gera snapshot reutilizável; não lê arquivos de credenciais."""
    ferramentas = {}
    for nome in ("python", "docker", "ollama", "node", "npm", "git", "nvidia-smi"):
        executavel = shutil.which(nome)
        info = {"caminho": executavel}
        if executavel and nome not in ("npm", "nvidia-smi"):
            info["versao"] = consultar([executavel, "--version"])
        ferramentas[nome] = info
    docker = ferramentas["docker"]["caminho"]
    ollama = ferramentas["ollama"]["caminho"]
    gpu = ferramentas["nvidia-smi"]["caminho"]
    return {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "projeto": str(projeto), "sistema": platform.platform(),
        "python_em_execucao": sys.executable, "cpu_logicas": os.cpu_count(),
        "ram_bytes": memoria_total(), "disco_livre_bytes": shutil.disk_usage(projeto).free,
        "ferramentas": ferramentas,
        "docker_servidor": consultar([docker, "info", "--format", "{{.ServerVersion}}"])
        if docker else {"disponivel": False},
        "modelos_ollama": consultar([ollama, "list"])
        if ollama else {"disponivel": False, "observacao": "CLI ausente; endpoint não verificado"},
        "gpu": consultar([gpu, "--query-gpu=name,memory.total", "--format=csv,noheader"])
        if gpu else {"disponivel": False, "observacao": "GPU não determinada"},
    }


def main():
    """Escreve JSON em stdout sem criar arquivos no projeto."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Raiz do projeto")
    argumentos = parser.parse_args()
    projeto = argumentos.project.resolve()
    if not projeto.is_dir():
        parser.error("O diretório do projeto não existe.")
    print(json.dumps(diagnosticar(projeto), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
