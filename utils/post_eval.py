# Eval command Processer
# Made by Tpmonkey

import subprocess
import shlex
import sys
import os

def format_str(text: str, uid: int) -> str:
    text = text.replace(f"evals/{uid}.py", "<string>")
    _list = text.split("\n")
    _list = [text.strip() for text in _list]
    return "\n".join(_list)

async def post_eval(code: str, uid: int):
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