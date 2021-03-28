var account=""
var password=""
oss_path="https://ride-v.oss-accelerate.aliyuncs.com/phone_sport/ws/"
cache_task_name=""

function update_local_password(){
    if ("account" in localStorage && localStorage["account"]!=""){
        account=localStorage["account"]
        password=localStorage["password"]
    }
}

function clear_local_password(){
    if ("account" in localStorage){
        localStorage["account"]=""
        localStorage["password"]=""
        account=""
        password=""
    }
}

function set_local_password(account_, password_){
    localStorage.setItem("account", account_)
    localStorage.setItem("password", password_)
}

function upload_kml(task_name){
    cache_task_name=task_name
    console.log(cache_task_name)
    document.getElementById('load_kml').click()
}

function callback_upload_kml(){
    for (var file_id=0; file_id<this.files.length; file_id++){
        console.log(this.files[file_id])
        var file=this.files[file_id]
        var file_name=file["name"]
        if (!file_name.includes(".kml")){
            break
        }
        var fr = new FileReader();
        fr.onload = function(e) {
            str_kml = e.target.result;
            if (cache_task_name!=""){
                send_kml(cache_task_name, str_kml)
            }
        };
        fr.readAsText(file);
    }    
}

function get_account_info(){
    if (account==""){
        return;
    }
    $.ajax({
        url: "../../user_info",
        type: 'POST',
        dataType: 'json',
        username: account, 
        password: password,
        success: function(data){
            if ("name" in data){
                if ("user_tasks" in data){
                    garage_count=data["user_tasks"].length
                    g_list=data["user_tasks"]
                    html_table="<table border=1>"
                    html_table=html_table+"<tr><th>任务名</th><th>kml</th><th>视频</th><th></th><th>开始时间</th><th>状态</th></tr>"
                    for(var i=0; i<garage_count; i++){
                        html_table=html_table+'<tr>'
                        html_table=html_table+'<td>'+g_list[i]["name"]+'</td>'
                        if (g_list[i]["has_kml"]){
                            html_table=html_table+'<td>'+'<a href="'+oss_path+g_list[i]["name"]+"/chamo.kml"+'">下载</a>'+'</td>'
                        }else{
                            html_table=html_table+'<td></td>'
                        }
                        html_table=html_table+'<td>'+'<a href="'+oss_path+g_list[i]["name"]+"/chamo.mp4"+'">下载</a>'+'</td>'
                        if (g_list[i]["edit_mode"]=="pending" || g_list[i]["edit_mode"]=="done"){
                            html_table=html_table+'<td></td>'
                        }else{
                            html_table=html_table+'<td>'+'<a href="#" onclick=upload_kml("'+g_list[i]["name"]+'")>上传</a>'+'</td>'
                        }
                        html_table=html_table+'<td>'+parseInt(g_list[i]["edit_time"])+'</td>'
                        html_table=html_table+'<td>'+g_list[i]["edit_mode"]+'</td>'
                        html_table=html_table+'</tr>'
                    }
                    html_table=html_table+"</table>"
                    document.getElementById("user_tasks").innerHTML=html_table
                }
                document.getElementById("account_info").innerHTML="<b>账号：</b>"+data["name"]
            }
        },
        error: function (request, status, error) {
            clear_local_password()
        }
    });
}

function login_regist(){
    var account = document.getElementById("account").value
    var password = document.getElementById("password").value
    $.ajax({
        url: "../../login_create",
        type: 'POST',
        dataType: 'json',
        data: { regist_data: JSON.stringify({"account":account, "password":password})},
        success: function(data){
            
            if (data[0]=="regist_ok"){
                set_local_password(account, password)
                update_local_password()
                alert("注册成功")
                document.getElementById("loginui").style.display = "none"
                get_account_info()
                get_proj_list()
            }else if(data[0]=="login_ok"){
                alert("登录成功")
                set_local_password(account, password)
                update_local_password()
                document.getElementById("loginui").style.display = "none"
                get_account_info()
                get_proj_list()
            }else if(data[0]=="password_wrong"){
                alert("密码错误")
            }else if(data[0]=="account_or_password_len_invalid"){
                alert("账号密码长度不符合要求")
            }
        },
    });
}

function send_kml(proj, str_kml){
    console.log(proj)
    $.ajax({
        type: 'POST',
        url: '../../send_kml',
        data: { proj: proj, str_kml:str_kml},
        username: account, 
        password: password,
        dataType: 'json',
        success: function(data) {
            if (data[0]=="ok"){
                get_account_info()
            }else{
                alert(data[0])
            }
        },
    });
}

function choose_task(proj){
    $.ajax({
        type: 'GET',
        url: '../../choose_task',
        data: { proj: proj},
        username: account, 
        password: password,
        dataType: 'json',
        success: function(data) {
            if (data[0]=="ok"){
                get_proj_list()
                get_account_info()
            }else{
                alert(data[0])
            }
        },
    });
}

function get_proj_list(){
    
    $.ajax({
        type: 'GET',
        url: '../../get_proj_list',
        data: { mode: "no_user"},
        dataType: 'json',
        success: function(data) {
            
            var str='<table border="1">'
            str=str+'<tr><td>路线名</td><td>原始视频</td><td>开始编辑</td></tr>'
            if (data.length>0){
                for(var i=0; i<data.length; i++){
                    var str_row="<tr>"
                    str_row=str_row+"<td>"+data[i]["name"]+"</td>"
                    str_row=str_row+"<td>"+'<a href="'+oss_path+data[i]["name"]+"/chamo.mp4"+'">视频</a>'+"</td>"
                    str_row=str_row+"<td>"+'<a href="#" onclick=choose_task("'+data[i]["name"]+'")>选择</a>'+"</td>"
                    str_row=str_row+"</tr>"
                    str=str+str_row
                }
            }
            str=str+"</table>"
            document.getElementById("no_user_tasks").innerHTML=str
        },
    });
}

$(document).ready(function(){
    $.ajaxSetup({
        async: false
    });
    update_local_password()
    console.log(account,password)
    get_account_info()
    var x = document.getElementById("loginui");
    if (password=="") {
        x.style.display = "block";
    } else {
        get_proj_list()
        x.style.display = "none";
    }
    inputNode = document.getElementById("load_kml");
    inputNode.addEventListener('change', callback_upload_kml, false)
})
