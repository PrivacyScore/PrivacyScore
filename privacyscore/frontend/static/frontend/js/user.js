function loadData() {

		
		$.ajax({
            url: apiUrl + '/info',
            type: 'GET',
			xhrFields: {
				withCredentials: true
			},
			success: function (data) {
				data = JSON.parse(data);
				console.log(data);
				
				document.getElementById("inputEmail").value = data.email;
				document.getElementById("firstname").value = data.firstname;
				document.getElementById("lastname").value = data.lastname;
				
			}
        });
	
}




function saveUserData() {
	
	var email = document.getElementById("inputEmail").value;
	var firstname = document.getElementById("firstname").value;
	var lastname = document.getElementById("lastname").value;
	var pw1 = document.getElementById("pw1").value;
	var pw2 = document.getElementById("pw2").value;
	
	document.getElementById("saveSuccess").style.display = "none";
	document.getElementById("saveError").style.display = "none";
	document.getElementById("differentPasswords").style.display = "none";
	
	$.ajax({
            url: apiUrl + '/edit',
            type: 'POST',
			xhrFields: {
				withCredentials: true
			},
			data: {
				"email": email,
				"firstname": firstname,
				"lastname": lastname,
				"pw": pw1,
				"pw2": pw2
			},
			success: function (data) {
				data = JSON.parse(data);
				console.log(data);
				
				if (data.hasOwnProperty("type") && data.type == "success") {
					document.getElementById("saveSuccess").style.display = "block";
				} else if (data.hasOwnProperty("type") && data.type == "error" && data.message == "Passwords do not match.") {
					document.getElementById("differentPasswords").style.display = "block";
				} else {
					document.getElementById("saveError").style.display = "block";
				}
				
				// document.getElementById("inputEmail").value = data.email;
				// document.getElementById("firstname").value = data.firstname;
				// document.getElementById("lastname").value = data.lastname;
				
			}
        });
}