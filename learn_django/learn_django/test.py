import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect('punc01dcv003',username='rlmasal',password='***')


def sshCom(command):
	stdin, stdout, stderr = ssh.exec_command(command)		
	output = str(stdout.read())[2:-3]
	return(output)

print(sshCom('ip route'))
print(sshCom('queue'))