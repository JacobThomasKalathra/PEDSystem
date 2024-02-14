//Ajax for loading email list of users/admins based on operation selected through radio button
function showAdmins(id_email){
  var chkRevoke = document.getElementById("revokeid");
  var emailDrpdwnObj = document.getElementById(id_email);
  var operation = chkRevoke.checked ? "revoke" : "remove";
  var defaultEmail = new Option("Select Email", "");
  $.ajax({
       url: '/fetch_users/'+operation,
       type: 'GET',

       success : function(data){
          var response = data.split(",");
          var response = JSON.parse(response);
          emailDrpdwnObj.innerHTML="";
          emailDrpdwnObj.appendChild(defaultEmail).disabled = true;;
          for ( var index = 0; index < response.length; index++)
          {
             var userEmail = response[index];
             var emailObj = new Option(userEmail, userEmail);
             emailDrpdwnObj.appendChild(emailObj);
          }
          return;
       }
    });
  return;
}    

function validateEmailfunction()
{
    
    var emailId= document.getElementsByClassName("emailvalidate");
    var filter= /^[a-zA-Z0-9]+[a-zA-Z0-9.!#%&'*+-/=?^_`{|}~]*\@oracle.com/;
    for(i=0;i<emailId.length;i++)
   {
    if (emailId[i].value == "" || !filter.test(emailId[i].value) )
        {
            alert("Please provide a valid Oracle email address");
            return false;
        }
}
}




function fun()
{
var Val1 = document.getElementById("ddlList1");
var Val1Value = Val1.value;
if (Val1Value == "")
{
alert("Please select a value");
return false;
} 


}



function anyvalidate() {
var server = document.getElementById("host");
var uname = document.getElementById("username");
var pwd = document.getElementById("password");
var remotedir = document.getElementById("remote_dir");
var time_zone = document.getElementById("time_zone");
if (server.value == ""&& uname.value == ""&& pwd.value == ""&& remotedir.value == "" && time_zone.value=="") 
	{
		alert( "Please fill at least one field " );
     return false;
	 }
	 }
