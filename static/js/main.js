mode=null
function get_proj_list(){
    $.ajax({
        type: 'GET',
        url: '../../get_proj_list',
        data: { mode: mode},
        dataType: 'json',
        success: function(data) {
            console.log(data)
            var str='<table border="1">'
            if (mode=="all"){
                str=str+'<tr><td>路线名</td><td>编辑者</td><td>编辑状态</td><td>开始日期</td><td>状态</td><td>信息</td><td></td></tr>'
            }else if(mode=="no_user"){
                str=str+'<tr><td>路线名</td></tr>'
            }else if(mode=="pending"){
                str=str+'<tr><td>路线名</td><td>编辑者</td><td>编辑状态</td><td>开始日期</td><td></td><td></td></tr>'
            }
            
            if (data.length>0){
                for(var i=0; i<data.length; i++){
                    var str_row="<tr>"
                    task=data[i]["task"]
                    status=data[i]["status"]
                    info=data[i]["info"]
                    if (!("task" in data[i])){
                        task=""
                        status=""
                        info=""
                    }
                    str_row=str_row+'<td onclick=set_proj_name("'+data[i]["name"]+'")>'+data[i]["name"]+"</td>"
                    if (mode=="all" || mode=="pending"){
                        str_row=str_row+'<td>'+data[i]["owner"]+"</td>"
                        str_row=str_row+'<td>'+data[i]["edit_mode"]+"</td>"
                        str_row=str_row+'<td>'+data[i]["edit_time"]+"</td>"
                    }
                    if (mode=="all"){
                        str_row=str_row+"<td>"+task+":"+status+"</td>"
                    }
                    if (mode=="pending"){
                        str_row=str_row+"<td>"+'<a href="#" onclick=pass_proj("'+data[i]["name"]+'")>通过</a>'+"</td>"
                        str_row=str_row+"<td>"+'<a href="#" onclick=fail_proj("'+data[i]["name"]+'")>失败</a>'+"</td>"
                    }
                    if (mode=="all"){
                        str_row=str_row+"<td>"+'<a href="#" onclick=reqeust_proc("'+data[i]["name"]+'")>处理</a>'+"</td>"
                        str_row=str_row+"<td>"+info+"</td>"
                    }
                    str_row=str_row+"</tr>"
                    str=str+str_row
                }
            }
            str=str+"</table>"
            document.getElementById("proj_list").innerHTML=str
        },
    });
}

function pass_proj(proj_name){
    $.ajax({
        type: 'GET',
        url: '../../verify_proj',
        data: {proj_name:proj_name,result:"ok"},
        dataType: 'json',
        success: function(data) {
            get_proj_list()
        },
    });
}

function fail_proj(proj_name){
    $.ajax({
        type: 'GET',
        url: '../../verify_proj',
        data: {proj_name:proj_name,result:"no"},
        dataType: 'json',
        success: function(data) {
            get_proj_list()
        },
    });
}

function set_proj_name(proj){
    document.getElementById("traj_input").value=proj
}

function reqeust_proc(proj_name){
    $.ajax({
        type: 'POST',
        url: '../../reqeust_proc',
        data: { proj_name: proj_name},
        dataType: 'json',
        success: function(data) {
            get_proj_list()
        },
    });
}

function modify_status(){
    var traj = document.getElementById("traj_input").value
    var task = document.getElementById("task_input").value
    var status = document.getElementById("status_input").value
    var owner = document.getElementById("owner_input").value
    var edit_mode = document.getElementById("edit_mode_input").value
    $.ajax({
        type: 'GET',
        url: '../../modify_status',
        data: {traj:traj,task:task,status:status, owner:owner, edit_mode:edit_mode},
        dataType: 'json',
        success: function(data) {
            get_proj_list()
        },
    });
}

function GetRequest() {
    var url = location.search;
    var theRequest = new Object();
    if (url.indexOf("?") != -1) {
        var str = url.substr(1);
        var strs = str.split("?");
        for (var i = 0; i < strs.length; i++) {
            theRequest[strs[i].split("=")[0]] = decodeURIComponent(strs[i].split("=")[1]);
        }
    }
    return theRequest;
}
    

$(document).ready(function(){
    $.ajaxSetup({
        async: false
    });
    url_paremeters_dic=GetRequest()
    
    mode = url_paremeters_dic['n']
    if (mode==null){
        mode="all"
    }
    get_proj_list()
})
