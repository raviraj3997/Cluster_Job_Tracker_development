from django.shortcuts import render, redirect
from django.contrib import messages
# Create your views here.

import ansys.dpf.core as dpf
from .utility_space import ClientSetup, GetJobs
from .Convergence_app import *
from .Convergence_calc import *
from .utility_space import *


ssh_client = ClientSetup()
get_jobs = GetJobs(ssh_client)


def help(request):
    args = {'link_str':'Login', 'link_url': 'login'}
    return render(request, 'help_page.html', args)


def login(request, error_msg = ''):
    args = {'link_str':'Help', 'link_url': 'help', 'error_msg':error_msg}
    return render(request, 'login_page.html',args)


def joblist(request):

    if request.method == "POST":
        uname = request.POST.get('uname')
        psw = request.POST.get('psw')
        # ssh_client = ClientSetup()

        if ssh_client.login_successful(uname,psw):
            # get_jobs = GetJobs(ssh_client)
            print(ssh_client.execute_command('ip route'))
            user_jobs_dict = get_jobs.get_user_jobs()
            # user_jobs_dict = {'ravi':[1, 100], 'rajesh':[5, 500]}
            args = {'link_str': 'Help', 'link_url': 'help', 'user_jobs_dict': user_jobs_dict, 'uname': uname}
            return render(request, 'job_selection.html', args)
        else:
            error_message = [
                "Login failed !!!",
                "Please correct the HOSTNAME\\HOST IP,username and password and try again."
            ]

            messages.success(request, error_message)
            return redirect("login") 
    else:
        return redirect("login")


def plot(request):
    if request.method == "POST":

        tab = request.POST.get('tab_control')
        if tab == "Completed":
            work_dir = request.POST.get('work_dir_completed')
            job_name = request.POST.get('job_name_completed')
            cores = request.POST.get('cores_completed')
        else:
            work_dir = request.POST.get('work_dir')
            job_name = request.POST.get('job_name')
            cores = request.POST.get('cores')

        set_dpf = DPF_GRPC_Settings(dpf)

        if not set_dpf.connect_remote_grpc_server(ip=SeverDetails.IP, port=SeverDetails.PORT):
            dpf_connection_error = [
                "Could not connect to the GRPC server.",
                "Check if server with IP ({}) and  port ({}) "
                "is running.".format(SeverDetails.IP, SeverDetails.PORT)
            ]

            messages.success(request, dpf_connection_error)
            args = {'link_str': 'Help', 'link_url': 'help'}
            return render(request, 'job_selection.html', args)

        plugin_load_error = loading_plugin(set_dpf)
        print("plugin_load_error")
        print(plugin_load_error)
        print("plugin_load_error")
        final_quanitities = []
        final_data = {}

        if plugin_load_error is None:
            gst_plugin_instance_error, gst_file_finding_error, gst_final_quanitities, gst_final_data = \
                read_gst_or_cnd_file(work_dir, job_name, set_dpf, 'gst')
            cnd_plugin_instance_error, cnd_file_finding_error, cnd_final_quanitities, cnd_final_data = \
                read_gst_or_cnd_file(work_dir, job_name, set_dpf, 'cnd')

        print(gst_final_quanitities)
        print(gst_file_finding_error)
        print(gst_plugin_instance_error)
        print("gst_plugin_instance_error")
        args = {'link_str': 'Help', 'link_url': 'help'}
        return render(request, 'plot_page.html', args)

    else:
        return redirect("login")


def loading_plugin(set_dpf):
    custom_plugin = PluginSettings(set_dpf.dpf)
    if not custom_plugin.load_plugin():
        error_message = "Custom plugin for custom operator is not loaded." \
                        "Check if file location ({}) and  custom library ({}) " \
                        "is correct.".format(PlugInDetails.PLUGIN_PATH, PlugInDetails.LIBRARY)
    else:
        error_message = None
    return error_message


def read_gst_or_cnd_file(work_dir, job_name, set_dpf, file_type):
    final_quanitities = []
    final_data = {}
    xml_reader = ReadXML(work_dir=work_dir, job_name=job_name, dpf=set_dpf.dpf)
    if not xml_reader.instantiate_operator():
        plugin_instance_error = "Custom operator could not be instantiated." \
                        "Check the version compatibility fo the custom plugin."
    else:
        plugin_instance_error = None
    file_finding_error = ""
    if plugin_instance_error is None:
        file_data = xml_reader.read_xml_file(file_type=file_type)
        if file_data is None:
            if file_type == 'gst':
                file_finding_error = "Could not find file in folder {}." \
                                     "".format(work_dir) + "Check if you have issued " \
                                                           "'/GST,ON,ON' command in APDL input file."
            else:
                file_finding_error = "Could not find file in folder {}." \
                                     "".format(work_dir) + "Check if you have issued " \
                                                           "'NLDIAG,CONT,ITER' command in APDL input file."
        else:
            file_finding_error = None
            final_quanitities, final_data = xml_reader.xml_to_dict(file_type=file_type, xml_file_data=file_data)

    return plugin_instance_error, file_finding_error, final_quanitities, final_data