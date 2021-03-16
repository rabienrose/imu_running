function get_proj_list(){
    $.ajax({
        type: 'POST',
        url: '../../get_proj_list',
        dataType: 'json',
        success: function(data) {
            console.log(data)
            var str='<table border="1">'
            str=str+'<tr><td>路线名</td><td>状态</td><td>信息</td><td></td></tr>'
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
                    str_row=str_row+"<td>"+data[i]["name"]+"</td>"
                    str_row=str_row+"<td>"+task+":"+status+"</td>"
                    str_row=str_row+"<td>"+'<a href="#" onclick=reqeust_proc("'+data[i]["name"]+'")>处理</a>'+"</td>"
                    str_row=str_row+"<td>"+info+"</td>"
                    str_row=str_row+"</tr>"
                    str=str+str_row
                }
            }
            str=str+"</table>"
            document.getElementById("proj_list").innerHTML=str
        },
    });
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

$(document).ready(function(){
    $.ajaxSetup({
        async: false
    });
    get_proj_list()
})
