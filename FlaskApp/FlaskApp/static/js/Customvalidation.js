//Verify passwords are same
function validate()
{
    var password = document.getElementById("regpassword").value;
    var repassword = document.getElementById("confirm_password").value;
    if(password != repassword)
    {
        alert("Passwords do not match.");
        return false;
    }
    return true;

}
//Dropdownlist Validation function
function validateDropdownlist()
{
        var dropdownlist= document.getElementsByClassName("dropdownlistvalidate");
        for(i=0;i<dropdownlist.length;i++)
        {
                if (dropdownlist[i].value == "default")
                {
                        alert("Please select a value from dropdown list");
                        //dropdownlist[i].style.borderColor="red";
                        return false;
                }
        }
        return
}
//Verify all fields have values
function validatetextfield()
{

        var textfield = document.getElementsByClassName("textfieldvalidate");
        //var txt = document.getElementById('txtGroup');
        // var filtertext = /^[a-zA-Z!”$%&’()*\+,\/;\[\\\]\^_`{|}~]+$/;

        var filtertext = /^[a-zA-Z0-9- _]*$/;
        for(i=0;i<textfield.length;i++)
        {

                if (textfield[i].value == "")
                {
                        alert("Please enter a value in text field");
                        return false;

                }
                else if(!filtertext.test(textfield[i].value))
                {
                        alert("Please enter valid characters");
                        return false;
                }
                return true;
        }

}

function validateEmptyField(){
        var emptyfield= document.getElementsByClassName("textemptyvalidate");

        for(i=0;i<emptyfield.length;i++)
        {

                if (emptyfield[i].value == "")
                {
                        alert("Please fill out all the fields");
                        return false;
                }
        }


}

//Email Validation function

function validateEmailfunction()
{

        var emailId= document.getElementsByClassName("emailvalidate");

        for(i=0;i<emailId.length;i++)
        {
                var filter= /^[a-zA-Z0-9.]+\@oracle.com$/;
                if (emailId[i].value == "" || !filter.test(emailId[i].value) )
                {
                        alert("Please provide a valid Oracle email address");
                        return false;
                }
        }


}

