from ast import Return
import paramiko
import pandas as pd
import xmltodict


class SeverDetails:
    IP = "10.18.19.239"
    PORT = 50052
    NAME = 'punc01dcv003'


class QueueDetails:
    SQUEUE = 'squeue'
    USER_COLUMN_HEADER = 'USER'
    JOBID_COLUMN_HEADER = 'JOBID'


class PlugInDetails:
    PLUGIN_PATH = r"/nfs/scratch1/ACE/rlmasal/PyAnsys/custom_plugin.so"
    LIBRARY = 'custom_plugin'


def textToList(data: str) -> list:
    data = data.replace('\\n', '\n')
    finalData = []
    lines = data.split("\n")
    for line in lines:
        lineData = line.split()
        lineDataNew = []
        for lineDataItem in lineData:
            try:
                lineDataNew.append(float(lineDataItem))
            except:
                lineDataNew.append(lineDataItem)
        finalData.append(lineDataNew)

    return finalData


class ClientSetup:
    def __init__(self) -> None:
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def execute_command(self, command: str) -> str:
        stdin, stdout, stderr = self.ssh.exec_command(command)
        output = str(stdout.read())[2:-3]
        return output

    def get_ip_address(self):
        out = self.execute_command('ip route')
        return out

    def login_successful(self, uname: str, pswd: str) -> bool:
        try:
            self.ssh.connect(SeverDetails.NAME, username=uname, password=pswd)
            return True
        except:
            return False


class GetJobs:
    def __init__(self, ssh_client) -> None:
        self.ssh_client = ssh_client

    def get_queue_data(self) -> list:
        queue_data = self.ssh_client.execute_command(QueueDetails.SQUEUE)
        return textToList(queue_data)

    def get_user_jobs(self) -> dict:
        data = self.get_queue_data()
        dfData_queue = []
        header_queue = data[0]
        data_queue_1 = data[1:]
        data_queue = []
        for item in data_queue_1:
            # print(len(item))
            if len(item) > 8:
                for i in range(len(item) - 8):
                    item.pop(-1)
            if len(item) < 8:
                for i in range(8 - len(item)):
                    item.append("")
            data_queue.append(item)
        # print(data_queue)
        df = pd.DataFrame(data_queue, columns=header_queue)
        dfData_queue.append(df)

        finalDfData_queue = pd.concat(dfData_queue)
        user_job_dict = {}

        for ind in finalDfData_queue.index:
            if finalDfData_queue[QueueDetails.USER_COLUMN_HEADER][ind] in user_job_dict.keys():
                user_job_dict[finalDfData_queue[QueueDetails.USER_COLUMN_HEADER][ind]].append(
                    int(finalDfData_queue[QueueDetails.JOBID_COLUMN_HEADER][ind]))
            else:
                user_job_dict[finalDfData_queue[QueueDetails.USER_COLUMN_HEADER][ind]] = [
                    int(finalDfData_queue[QueueDetails.JOBID_COLUMN_HEADER][ind])]

        return user_job_dict


class DPF_GRPC_Settings:
    def __init__(self, dpf) -> None:
        self.dpf = dpf

    def run_remote_grpc_server(self, ip: str):
        pass

    def connect_remote_grpc_server(self, ip: str, port: int = 50052) -> bool:
        try:
            self.dpf.connect_to_server(ip=ip, port=port)
            return True
        except:
            return False


class PluginSettings:
    def __init__(self, dpf) -> None:
        self.dpf = dpf

    def load_plugin(self) -> bool:
        try:
            self.dpf.load_library(PlugInDetails.PLUGIN_PATH, PlugInDetails.LIBRARY)
            return True
        except:
            return False


class ReadXML:
    def __init__(self, work_dir, job_name, dpf) -> None:
        self.workingDir = work_dir
        self.jobName = job_name
        self.dpf = dpf
        self.op = None

    def instantiate_operator(self) -> bool:
        try:
            self.op = self.dpf.operators.utility.custom_tracker()
            return True
        except:
            return False

    def read_xml_file(self, file_type: str):
        try:
            self.op.inputs.file_to_read(self.workingDir + "/" + self.jobName + "." + file_type)
            return self.op.outputs.file_string.get_data()
        except:
            return None

    def xml_to_dict(self, file_type: str, xml_file_data: str):

        if file_type == 'cnd':
            doc_contactTracker = xmltodict.parse(xml_file_data)

            allLoadStepData_contactTracker = doc_contactTracker['SOLUTION']

            columnHeaders_contactTracker = []
            for colHead_contactTracker in allLoadStepData_contactTracker['HEADER']['COLUMN']:
                columnHeaders_contactTracker.append(colHead_contactTracker['#text'])

            columnHeaders_contactTracker.pop(0)
            columnHeaders_contactTracker.insert(0, 'Time')
            columnHeaders_contactTracker.insert(1, 'Load Step')
            columnHeaders_contactTracker.insert(2, 'Sub-step')
            columnHeaders_contactTracker.insert(3, 'Cum Iter')
            columnHeaders_contactTracker.insert(0, 'Contact Pair ID')

            dfData_contactTracker = {}
            cum_itr = 0
            for colData_contactTracker in allLoadStepData_contactTracker['COLDATA']:
                # if (int(colData_contactTracker['@ITERATION']) != 0 or float(colData_contactTracker['@TIME']) == 0.0):
                if (int(colData_contactTracker['@ITERATION']) != 0):
                    data = textToList(colData_contactTracker['#text'])
                    for item in data:
                        if int(item[0]) not in dfData_contactTracker.keys():
                            dfData_contactTracker[int(item[0])] = []
                        key = int(item.pop(0))
                        item.insert(0, float(colData_contactTracker['@TIME']))
                        item.insert(1, int(colData_contactTracker['@LOAD_STEP']))
                        item.insert(2, int(colData_contactTracker['@SUBSTEP']))
                        item.insert(3, int(cum_itr))
                        item.insert(0, int(key))
                        dfData_contactTracker[key].append(item)
                    cum_itr = cum_itr + 1

            dfData_contactTracker_list = []
            for key, val in dfData_contactTracker.items():
                df = pd.DataFrame(val, columns=columnHeaders_contactTracker)
                dfData_contactTracker_list.append(df)

            dfData_contactTracker = pd.concat(dfData_contactTracker_list)

            finalDfData_contactTracker = dfData_contactTracker.reset_index()

            finalDfData_contactTracker['Time Shift'] = finalDfData_contactTracker["Time"].shift(-1)
            finalDfData_contactTracker['Sub-step Shift'] = finalDfData_contactTracker["Sub-step"].shift(-1)
            finalDfData_contactTracker['Load Step Shift'] = finalDfData_contactTracker["Load Step"].shift(-1)

            AllQuantities_Cont = list(finalDfData_contactTracker.columns)
            AllQuantities_Cont.remove('index')
            AllQuantities_Cont.remove('Cum Iter')
            AllQuantities_Cont.remove('Contact Pair ID')
            AllQuantities_Cont.remove('Time Shift')
            AllQuantities_Cont.remove('Sub-step Shift')
            AllQuantities_Cont.remove('Load Step Shift')
            AllQuantities_Cont.remove('Sub-step')
            AllQuantities_Cont.remove('Load Step')
            AllQuantities_Cont.remove('Contact pair force criterion')
            AllQuantities_Cont.remove('Contact pair force convergence norm')
            AllQuantities_Cont.append('Contact Convergence')

            final_data = finalDfData_contactTracker
            final_quanitities = AllQuantities_Cont
        else:
            doc_convergence = xmltodict.parse(xml_file_data)
            allLoadStepData_convergence = doc_convergence['SOLUTION']['LOADSTEPDATA']
            dfData_convergence = []
            for stepData_convergence in allLoadStepData_convergence:
                columnHeaders_convergence = []
                for colHead_convergence in stepData_convergence['HEADER']['COLUMN']:
                    columnHeaders_convergence.append(colHead_convergence['#text'])
                colData_convergence = stepData_convergence['COLDATA']
                data = textToList(colData_convergence)
                df = pd.DataFrame(data, columns=columnHeaders_convergence)
                dfData_convergence.append(df)

            dfData_convergence = pd.concat(dfData_convergence)

            finalDfData_convergence = dfData_convergence.reset_index()

            finalDfData_convergence['Time Shift'] = finalDfData_convergence["Time"].shift(-1)
            finalDfData_convergence['Sub-step Shift'] = finalDfData_convergence["Sub-step"].shift(-1)
            finalDfData_convergence['Load Step Shift'] = finalDfData_convergence["Load Step"].shift(-1)

            AllQuantities_Conv = []

            if "F   CRIT" in columnHeaders_convergence:
                AllQuantities_Conv.append("Force Convergence")
            if "U   CRIT" in columnHeaders_convergence:
                AllQuantities_Conv.append("Displacement Convergence")
            if "Max DOF Incr" in columnHeaders_convergence:
                AllQuantities_Conv.append("Max DOF Increment")
            if "Max Resi F" in columnHeaders_convergence:
                AllQuantities_Conv.append("Max Residual Force")
            if "Line Search Parameter" in columnHeaders_convergence:
                AllQuantities_Conv.append("Line Search")

            AllQuantities_Conv.append("Time")

            if "Time Incr" in columnHeaders_convergence:
                AllQuantities_Conv.append("Time Increment")

            final_data = finalDfData_convergence
            final_quanitities = AllQuantities_Conv

        return final_quanitities, final_data
