function singleSearch() {
	var value = document.getElementById("singleSearchField").value;
	
	value = value.replace(/\//g, '%2F');
	value = value.replace(/:/g, '%3A');
	
	var lang = getUrlVars()["lang"];
	if (lang == null || lang.length<1) {
		lang = "de";
	}
	
	if (value != null && value.length>1) {
		window.location.href = "lookup.html?q=" + value + "&lang=" + lang;
	} else {
		document.getElementById("singleSearchField").value = "http://www.uni-siegen.de/";
	}
	
}


function logout() {
	var logout = getUrlVars()["logout"];
	
	if (logout != null && logout == "true") {
		
		$.ajax({
            url: apiUrl + '/logout',
            type: 'GET',
			xhrFields: {
				withCredentials: true
			},
            success: function (data) {
				setCookie("login", "false");
				setCookie("userid", "");
				console.log(data);
				var lang = getUrlVars()["lang"];
				window.location.href = "index.html?lang=" + lang;
				
            }
        });
		
	}
	

}