"""
Eval Command processor, Can execute python file.
Idea by Python Discord Team (https://github.com/python-discord/snekbox)
Re-create by Tpmonkey
"""

import os
import sys
import shlex
import subprocess

__all__ = ("post_eval", )

def format_str(text: str, uid: int) -> str:
    """ Format output to hide file location. """
    text = text.replace(f"evals/{uid}.py", "<string>")
    _list = text.split("\n")
    _list = [text.strip() for text in _list]
    return "\n".join(_list)

async def post_eval(code: str, uid: int):
    """ Evaluvate code and return output, Can only be use by Admin. """
    path = f"evals/{uid}.py"

    with open(path, "w") as f:
        f.write(str(code))
        f.close()

    cm = f"{sys.executable} {path}"

    args = shlex.split(cm)
    p = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        p.kill()
        output = "TERMINATED, Time out!"
        code = 2
    else:
        output = p.stdout.read()
        code = p.returncode
    
    output = format_str(output, uid)
    os.remove(path)

    return (output.rstrip("\n"), code)