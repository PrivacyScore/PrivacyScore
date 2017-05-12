var global_token = '';
var global_unique_id = '';

var langData;

$( document ).ready(function() {
	
	console.log(getCookie("login"));
	if (getCookie("login") != null && getCookie("login") == "true") {
		document.getElementById("privateCheckbox").disabled = false;
		document.getElementById("privateListDisabled").style.display = "none";
	}
	
	var lang = getUrlVars()["lang"];
	if (lang == null) {
		lang = "de";
	}
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data) {
		langData = data;
	
	
		// when loading site, check for url variables
		var listid = getUrlVars()["list"];
		var groupid = getUrlVars()["group"];
		var edit = getUrlVars()["edit"];
		var newListFromOld = getUrlVars()["n"];
		if (edit != null && edit == "true") {
			document.getElementById("editListDescription").style.display = "inline";
			document.getElementById("search").style.display = "block";
			document.getElementById("searchButton").style.display = "inline";
			document.getElementById("afterLoad").style.display = "none";
			document.getElementById("rememberToken").style.display = "none";
			document.getElementById("scanButton").classList.remove("disabled");
		}
		if (listid != null) {
			var getdata = listid;
			if (newListFromOld == "true") {
				loadListFromOld(getdata, groupid);
			} else {
				loadList(getdata, false);
			}
		} else if (getUrlVars()["listid"] != null && getUrlVars()["listid"].length > 0){
			// list urlVar ist not token bu list_id -> find the right token for that list
			listid = getUrlVars()["listid"];
			$.ajax({
				url: apiUrl + '/GetToken/' + listid + '/',
				type: 'GET',
				xhrFields: {
					withCredentials: true
				},
				success: function (data) {
					data = data;
					console.log(data);
					loadList(data.token, false);
				}
			});
			
			
		} else {
			//if no list id in url -> draw an empty table
			drawTable(1,5);
			setUpload();
		}
			
	//	$.ajax({
	 //url: url,
	 //dataType: "jsonp",
	 //async: false,
	 // jsonpCallback: "callback"
	//});
});

});


function callback(json){
	// callback function to load a list from server
	//setTitle(json.name);
  console.log(json);
	setHeader1(json.name);
	setDescription(json.description);
	setTags(json.tags.toString());
	setPrivate(json.isprivate);
	setScannedLink(json.token);
	setUpload();
  
	var columns = json.columns.length;
	var rows = json.sites.length;
  
	drawTable(columns, rows);
	fillTable(createTableHeadContent(json), createTableBody(json));
	//fillTable(createTableHeadContent(json), null);
	
	// set height for table body
	var height = calculateHeight(rows);
	document.getElementsByTagName("tbody").item(0).style.maxHeight = ""+height+"px";
}

function saveButton(scan) {
	document.getElementById("rememberToken").style.display = "none";
	document.getElementById("scanButton").classList.remove("disabled");
	if (global_token == '') {
		// case: no id because new list should be created
		createNewList(scan);
	} else {
		// case: user is editing a list and wants to update it, no new list is created
		updateList(scan);
	}
}

function scanButton() {
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for url column
	var columnsReady = true;
	// check if all columns have names
	for (var i=0; i<columns; i++) {
		var id = "h-" + i;
		if (document.getElementById(id).getElementsByTagName("input").item(0).value.length<1) {
			columnsReady = false;
		}
	}
	
	if (!columnsReady) {
		//alert("Bitte tragen Sie für jede Spalte einen Namen ein!");
		alert(langData.list.alerts.columnsError);
	} else if (confirm(langData.list.confirms.scanList)) {
		var ready = false;
			while (!ready) {
				var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
				
				if (rows<=1) {
					break;
				}
				
				// iterate through all rows, if a row is empty, delete and break
				for (var i=0; i<rows; i++) {
					var id = "" + i + "-link";
					if (document.getElementById(id).value.length<1) {
						deleteRow(i);
						break;
					}
				}
				rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
				// check if all rows have url
				ready = true;
				for (var i=0; i<rows; i++) {
					var id = "" + i + "-link";
					if (document.getElementById(id).value.length<1) {
						ready = false;
					}
				}
			}
			var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
			if (rows <1) {
				//alert("Bitte geben Sie mindestens eine Website mit URL an!");
				alert(langData.list.alerts.noRowError);
			} else {
				saveButton(true);
			}
	}
}

function loadListFromOld(id, group) {
	$.get(apiUrl + "ShowScannedList/" + id + "/" + group, function (jsonString) {
	data = jsonString;
	console.log(1);
	console.log(data);
	// check for error
	if ((data.hasOwnProperty("type") && data.type == "error") || data.length < 1) {
		// if error -> alert error and draw an empty table
		//alert("Keine Liste zum eingegebenen Token vorhanden!");
		alert(langData.list.alerts.noListForToken);
		//drawTable(3,5);
	} else {
		// if no error -> callback function
		callback(data);
		global_token = "";
		global_unique_id = "";		
		document.getElementsByTagName("content").item(0).style.display = "block";
		document.getElementById("notEditable").style.display = "none";
	}
});
}

function loadList(getdata, newListFromOld) {
	global_token = getdata;
	$.get(apiUrl + "/ShowList/" + getdata + '/', function (jsonString) {
	data = jsonString;
	// check for error
	if ((data.hasOwnProperty("type") && data.type == "error") || data.length < 1) {
		// if error -> alert error and draw an empty table
		//alert("Keine Liste zum eingegebenen Token vorhanden!");
		alert(langData.list.alerts.noListForToken);
		//drawTable(2,5);
	} else if ((data.editable == false) && !newListFromOld) {
		// check if editable == false
		var panel = document.getElementById("notEditable");
		console.log(data);
		document.getElementsByTagName("content").item(0).style.display = "none";
		panel.style.display = "block";
		panel.getElementsByTagName("a").item(0).href = "./scannedList.html?list=" + data.id;
	} else {
		document.getElementById("afterLoad").style.display = "inline";
		document.getElementById("deleteButton").style.display = "inline";
		if (getCookie("login") != null && getCookie("login") == "true" && getCookie("userid") != null && getCookie("userid") != data.userid.$oid) {
			document.getElementById("claimListButton").style.display = "inline";
		}
		// if no error -> callback function
		console.log(data);
		callback(data);
		//global_token = data.token;
		global_unique_id = data.id;
		if (newListFromOld) {
			resetToken(data);
		}
	}
});
}

function createNewList(scan) {
	var req = {
			"listname": "",
			"description": "",
			"tags": [],
			"isprivate": false,
			"columns": [{"name": "", "visible": true}, {"name": "", "visible": true}],
			"userid": getCookie("userid")
        }
		
        $.ajax({
            url: apiUrl + '/SaveList/',
            type: 'POST',
            data: JSON.stringify(req),
            headers: {
                'Content-Type': 'application/json; charset=utf-8;'
            },
            success: function (data) {
				console.log(data);
				json = data;
				json = json;
				setScannedLink(json.token);
				global_token = json.token;
				global_unique_id = json.list_id	//TODO??
				updateList(scan);
				if (!scan) {
					var tokenDiv = document.getElementById("showToken");
					tokenDiv.style.display = "inline";
					tokenDiv.getElementsByTagName("span").item(1).innerHTML = global_token;
					//alert ("Ihre Liste wurde gespeichert unter dem Token " + global_token);	//todo
				}
            }
        });
}

function updateList(scan) {
	var id = global_token;
	
	var name = document.getElementById("name").value;
	var description = document.getElementById("description").value;
	var tags = document.getElementById("tags").value.replace(/, /g, ',').split(",");
	var isprivate = document.getElementById("privateCheckbox").checked;
	var columns = [];
	for (var columnIndex = 0; columnIndex < document.getElementById("list_table").getElementsByTagName("th").length-1; columnIndex++) {
		var headID = "h-"+columnIndex;
		var value = document.getElementById(headID).getElementsByTagName("input").item(0).value;
		var visible = true;
		var itemIndex = document.getElementById(headID).getElementsByTagName("label").length-1;
		if (document.getElementById(headID).getElementsByTagName("label").item(itemIndex).className == "glyphicon glyphicon-eye-close") {
			visible = false;
		}
		var helpColumn = {"name": value, "visible": visible};
		
		columns.push(helpColumn);
	}
	
	var req = {
		"token": id,
		"listname": name,
		"description": description,
		"tags": tags,
		"isprivate": isprivate,
		"columns": columns
    }
	console.log(req);
        $.ajax({
            url: apiUrl + '/UpdateList/',
            type: 'POST',
            data: JSON.stringify(req),
            headers: {
                'Content-Type': 'application/json; charset=utf-8;'
            },
            success: function (data) {
                //$("section").html(data);
				var json = data;
				if (json.hasOwnProperty("type") && json.hasOwnProperty("message") && json.type == "success" && json.message == "ok") {
					updateSites(global_unique_id, scan);
				}
            }
        });
	//window.location.href = window.location.href + "?list=" + id;
}

function updateSites(list_id, scan) {
	console.log(list_id);
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column
	
	var sites =  [];
	
	for (var rowIndex=0; rowIndex<rows; rowIndex++) {
		var column_values = [];
		for (var columnIndex=0; columnIndex<columns; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			column_values.push(document.getElementById(id).value);
		}
		var id = '' + rowIndex + '-link';
		var url = document.getElementById(id).value;
		var tempRow = {
			"list_id": list_id,
			"url": url,
			"column_values": column_values
		}
		sites.push(tempRow);
	}
	
	var req = {"listid": list_id, "sites": sites};
	
	console.log(req);

        $.ajax({
            url: apiUrl + '/SaveSite/',
            type: 'POST',
            data: JSON.stringify(req),
            headers: {
                'Content-Type': 'application/json; charset=utf-8;'
            },
            success: function (data) {
                if (scan) {
					scanList(scan);
				};
            }
        });
}

function scanList() {
		if (document.getElementById("name").value == "") {
			//alert("Bitte geben Sie einen Namen für Ihre Liste ein.");
			alert(langData.list.alerts.noNameError);
		} else {
			var req = {"listid": global_unique_id};
			$.ajax({
				url: apiUrl + '/ScanList/',
				type: 'POST',
				data: JSON.stringify(req),
				headers: {
					'Content-Type': 'application/json; charset=utf-8;'
				},
				success: function (data) {
					console.log(data);
					//if (confirm("Die gescannte Liste finden Sie unter der ID " + global_unique_id) || true) {
						window.location.href = "scannedList.html?list=" + global_unique_id;
					//}
				}
			});
		}
}

function searchToken() {
	var token = document.getElementById("search").value;
	if (token == "") {
		//alert("Kein Token eingegeben!");
		alert(langData.list.alerts.noTokenEntered);
	} else {
		loadList(token, false);
		document.getElementById("listDeleted").style.display = "none";
	}
}

function resetToken(json) {
	global_token = '';
	
	callback(json);
	
	document.getElementsByTagName("content").item(0).style.display = "block";
	document.getElementById("notEditable").style.display = "none";
}

function setScannedLink(listID) {
	var url = "http://PrivacyScore.de/scannedList.html?list=" + listID;
	//document.getElementById("scannedLink").getElementsByTagName("b").item(0).innerHTML = "<a href='" + url + "'>" + "hier" + "</a>";
	//document.getElementById("scannedLink").style.display = "inline";
}

function setTitle(text) {
	document.getElementsByTagName("head").item(0).getElementsByTagName("title").item(0).innerHTML = "PrivacyScore - Neue Liste erstellen";
}

function setHeader1(text) {
	document.getElementById("name").value = text;
}

function setDescription(text) {
	document.getElementById("description").value = text;
}

function setTags(text) {
	document.getElementById("tags").value = text.toString().replace(/,/g,", ");
}

function setPrivate(isprivate) {
	console.log(isprivate);
	document.getElementById("privateCheckbox").checked = isprivate;
}

function createTableHeadContent(json) {
	var tableHeadContent = [];
	for (var i=0; i<json.columns.length; i++) {
		var helpColumn = [];
		helpColumn.push(json.columns[i].visible);
		helpColumn.push(json.columns[i].name); // TODO: change back to columns[i].name when default visibility is available
		tableHeadContent.push(helpColumn);
	}
	return tableHeadContent;
}

function createTableBody(json) {
	var tableBody = [];
	
	for (var rowIndex=0; rowIndex<json.sites.length; rowIndex++) {
		var row = [];
		for (var columnIndex=0; columnIndex<json.sites[rowIndex].column_values.length; columnIndex++) {
			row.push(json.sites[rowIndex].column_values[columnIndex]);
		}
		row.push(json.sites[rowIndex].url); //push url to the end of the row
		tableBody.push(row);
	}
	return tableBody;
}

//id: row-column

function readTableBody() {
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column
		
	var tableBody = [];
		
	for (var rowIndex=0; rowIndex<rows; rowIndex++) {
		var row = [];
		for (var columnIndex=0; columnIndex<columns; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			row[columnIndex] = document.getElementById(id).value;
		}
		var id = '' + rowIndex + '-link';
		row.push(document.getElementById(id).value);
		tableBody.push(row);
	}
	return tableBody;
}

function readTableHead() {
	
	var columns = document.getElementById('list_table').getElementsByTagName('th').length-1; //-1 for first column
	
	var tableHeadContent = [];
	
	for (var columnIndex=0; columnIndex<columns; columnIndex++) {
		var id = 'h-' + columnIndex;
		var helpArray = [];
		var itemIndex = document.getElementById(id).getElementsByTagName("label").length-1;
		if (document.getElementById(id).getElementsByTagName("label").item(itemIndex).className == "glyphicon glyphicon-eye-close") {
			helpArray.push(false);
		} else {
			helpArray.push(true);
		}
		helpArray.push(document.getElementById(id).getElementsByTagName("input").item(0).value);
		tableHeadContent.push(helpArray);
	}
	return tableHeadContent;
}

function fillTable(tableHeadContent, tableBody) {
	// fill tableHead
	for (var columnIndex=0; columnIndex<tableHeadContent.length; columnIndex++) {
		var id = 'h-' + columnIndex;
		var itemIndex = document.getElementById(id).getElementsByTagName("label").length-1;
		if (tableHeadContent[columnIndex][0]) {
			document.getElementById(id).getElementsByTagName("label").item(itemIndex).className = "glyphicon glyphicon-eye-open";
		} else {
			document.getElementById(id).getElementsByTagName("label").item(itemIndex).className = "glyphicon glyphicon-eye-close";
		}
		document.getElementById(id).getElementsByTagName("input").item(0).value = tableHeadContent[columnIndex][1];
	}
	// fill tableBody
	for (var rowIndex=0; rowIndex<tableBody.length; rowIndex++) {
		// link is at the end of the row array
		var id = '' + rowIndex + '-link';
		document.getElementById(id).value = tableBody[rowIndex][tableBody[rowIndex].length-1];
		for (var columnIndex=0; columnIndex<tableBody[rowIndex].length-1; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			document.getElementById(id).value = tableBody[rowIndex][columnIndex];
		}
	}
}

function addRow(number) {
	
	var tableHeadContent = readTableHead();
	var tableBody = readTableBody();
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column

	drawTable(columns, rows+number);
	
	fillTable(tableHeadContent, tableBody);
	
	var height = calculateHeight(rows+number);
	document.getElementsByTagName("tbody").item(0).style.maxHeight = ""+height+"px";
		
}

function addColumn() {
	
	var tableHeadContent = readTableHead();
	var tableBody = readTableBody();
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column
	
	drawTable(columns+1, rows);
	
	fillTable(tableHeadContent, tableBody);
}

function drawTable(columns, rows) {
	var tableHead = '<tr>';
	// add tableHead the first column (link)
	tableHead += '<th id="h-link"><p type="text" class="form-control-static" style="padding-left:30px;">URL (http://...)</p></th>';	 //TODO? CHANGE URL http://...
	for (var columnIndex=0; columnIndex<columns; columnIndex++) {
		tableHead += '<th id="h-'
		tableHead += columnIndex;
		tableHead += '">';
		if (columns>0) {
			tableHead += '<label class="glyphicon glyphicon-remove-circle" data-toggle="tooltip" title="' + langData.list.tooltips.deleteColumn + '"  onclick="deleteColumn(';
			tableHead += columnIndex;
			tableHead += ');"></label>';
		}
		if (columnIndex!=0) {
			tableHead += '<label class="glyphicon glyphicon-circle-arrow-left" data-toggle="tooltip" title="' + langData.list.tooltips.moveColumn + '" " onclick="moveColumnLeft(';
			tableHead += columnIndex;
			tableHead += ');"></label>';
		}
		if (columnIndex!=columns-1) {
			tableHead += '<label class="glyphicon glyphicon-circle-arrow-right" data-toggle="tooltip" title="' + langData.list.tooltips.moveColumn + '" onclick="moveColumnRight(';
			tableHead += columnIndex;
			tableHead += ');"></label>';
		}
		tableHead += '<label class="glyphicon glyphicon-eye-open" data-toggle="tooltip" title="' + langData.list.tooltips.visibleColumn + '" onclick="setColumnVisible(';
		tableHead += columnIndex;
		tableHead += ');"></label>';
		tableHead += '<input type="text" class="form-control" style="width:100%;" /></th>';
	}
	tableHead += '</tr>';
	
	var tableBody = '';
	for (var rowIndex=0; rowIndex<rows; rowIndex++) {
		tableBody += '<tr>';
		// add the first column (link)
		tableBody += '<td>';
		tableBody += '<label class="glyphicon glyphicon-remove-circle" style="padding-top:0px;" data-toggle="tooltip" title="' + langData.list.tooltips.deleteRow + '" onclick="deleteRow(';
		tableBody += rowIndex;
		tableBody += ');"></label>';
		tableBody += '<input style="width:85%; display:inline-block;" placeholder="http://..." type="text" class="form-control" id="';
		tableBody += '' + rowIndex + '-link';
		tableBody += '" />';
		for (var columnIndex=0; columnIndex<columns; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			tableBody += '<td>';
			tableBody += '<input style="width:100%;" type="text" class="form-control" id="';
			tableBody += id;
			tableBody += '" /></td>'; 
		}
		tableBody += '</tr>';
	}
	
	document.getElementById('list_table').getElementsByTagName('thead').item(0).innerHTML = tableHead;
	document.getElementById('list_table').getElementsByTagName('tbody').item(0).innerHTML = tableBody;
}

function deleteColumn(deletedColumn) {
	
	if (confirm(langData.list.confirms.deleteColumn)) {
	var tableHeadContent = readTableHead();
	var tableBody = readTableBody();
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column

	
	drawTable(columns-1, rows); //-1 to delete column
	
	var newTableHeadContent = [];
	var newTableBody = [];
	
	for (var i=0; i<columns; i++) {
		if (i!=deletedColumn) {
			newTableHeadContent.push(tableHeadContent[i]);
			//newTableBody.push(tableBody[i]);
		}
	}
	for (var i=0; i<rows;i++) {
		var row = [];
		for (var j=0; j<columns+1; j++) {	//+1 for the last value in row array (link)
			if (j!=deletedColumn) {
				row.push(tableBody[i][j]);
			}
		}
		newTableBody.push(row);
	}
		
		fillTable(newTableHeadContent, newTableBody);
	}
}

function switchColumns(column1, column2) {
	
	var tableHeadContent = readTableHead();
	var tableBody = readTableBody();
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column
	
	var newTableHeadContent = JSON.parse(JSON.stringify(tableHeadContent));
	newTableHeadContent[column1] = tableHeadContent[column2];
	newTableHeadContent[column2] = tableHeadContent[column1];
	
	var newTableBody = JSON.parse(JSON.stringify(tableBody));
	
	for (var i=0; i<rows; i++) {
		newTableBody[i][column1] = tableBody[i][column2];
		newTableBody[i][column2] = tableBody[i][column1];
	}
	
	drawTable(columns,rows);
	fillTable(newTableHeadContent, newTableBody);
}

function moveColumnRight(column) {
	switchColumns(column, column+1);
}

function moveColumnLeft(column) {
	switchColumns(column, column-1);
}

function deleteRow(number) {
	
	var rows = document.getElementById('list_table').getElementsByTagName('tr').length - 1; //-1 for table head
	var columns = document.getElementById('list_table').getElementsByTagName('th').length - 1; //-1 for first column
	
	if (rows > 1) {
		var tableHeadContent = readTableHead();
		var tableBody = readTableBody();
		
		
		var newTableBody = [];
		for (var i=0; i<tableBody.length; i++) {
			if (i!=number) {
				newTableBody.push(tableBody[i]);
			}
		}
		
		drawTable(columns, rows-1);
		fillTable(tableHeadContent, newTableBody);
	} else {
		//alert("Letzte Reihe kann nicht gelöscht werden!")
		alert(langData.list.alerts.deleteLastRow);
	}
	// set height for table body
	var height = calculateHeight(rows);
	document.getElementsByTagName("tbody").item(0).style.maxHeight = ""+height+"px";	
}

function setColumnVisible(columnIndex) {
	var id = 'h-' + columnIndex;
	var itemIndex = document.getElementById(id).getElementsByTagName("label").length-1;
	var value = document.getElementById(id).getElementsByTagName("label").item(itemIndex).className;
	
	if (value.indexOf("open")>0) {
		document.getElementById(id).getElementsByTagName("label").item(itemIndex).className = "glyphicon glyphicon-eye-close";
	} else {
		document.getElementById(id).getElementsByTagName("label").item(itemIndex).className = "glyphicon glyphicon-eye-open";
	}
	
}

function scrollToCSV() {
		document.getElementById("csvUpload").scrollIntoView();
}

function showUploadHelp() {
	if (document.getElementById("uploadHelp").style.display == "none") {
		document.getElementById("uploadHelp").style.display = "";
	} else {
		document.getElementById("uploadHelp").style.display = "none";
	}
}

function scan() {
	var sure = confirm(langData.list.confirms.scanList);
}

function calculateHeight(rows) {
	var height = Math.min($(window).height()-320,rows*39);
	if ($(window).height()-450 < rows*39) {
		height = $(window).height()-320
	} else {
		height = (rows)*51;
	}
	return height;
}

function setUpload() {
	
var fileInput = $('#files');
var uploadButton = $('#uploadButton');

uploadButton.on('click', function() {
    if (!window.FileReader) {
        alert('Your browser is not supported')
    }
    var input = fileInput.get(0);
    
    // Create a reader object
    var reader = new FileReader();
	var reader2 = new FileReader();
    if (input.files.length) {
        var textFile = input.files[0];
		console.log(textFile);
        reader.readAsText(textFile, "ISO-8859-1");
		reader2.readAsText(textFile, "utf-8");
		$(reader).on('load', importCSV);
		$(reader2).on('load', importCSV);
    } else {
        //alert('Keine Datei ausgewählt!');
		alert(langData.list.alerts.noFileSelected);
    } 
});
}

function importCSV(e) {
    var file = e.target.result,
        results;
		// check for unknown characters in utf-8 and ISO-8859-1
		// if no unknown characters for both, file is loaded with both and ISO-8859-1 is used
		if (file.indexOf('�')==-1 && file.indexOf('¤')==-1) {
			if (file && file.length) {
				if (checkCSV(file)) {
					results = file.split("\n");
					
					var helpTableHead = results[0].split(",");
					var tableHeadContent = [];
					// remove the first entry in tableHead (Link)
					for (var i=1; i<helpTableHead.length; i++) {
						tableHeadContent.push([true, helpTableHead[i]]);
					}
					
					var columns = tableHeadContent.length;
					var rows = results.length-1;	//-1 for tableHead
					
					var tableBody = [];
					for (var rowIndex=1; rowIndex<results.length; rowIndex++) {
						var currentRow = results[rowIndex].split(",");
						var helpRow = [];
						for (var columnIndex=1; columnIndex<currentRow.length; columnIndex++) {
							helpRow.push(currentRow[columnIndex]);
						}
						helpRow.push(currentRow[0]);	// push the link at the end of the row
						tableBody.push(helpRow);
					}
					document.getElementById("fileError").style.display = "none";
					document.getElementById("fileSuccess").style.display = "inline";
					drawTable(columns, rows);
					fillTable(tableHeadContent, tableBody);
					
					return 1;
				} else {
					// case: csv file is not valid
					document.getElementById("fileError").style.display = "inline";
					document.getElementById("fileSuccess").style.display = "none";
				}
				
			}
		}
		return -1;
		
}

function checkCSV(csv) {
	var result = true;
	var rows = csv.split("\n");
	// get number of columsn from first row
	var numberOfColumns = rows[0].split(",").length;
	for (var i=0; i<rows.length; i++) {
		if (rows[i].split(",").length != numberOfColumns) {
			result = false;
		}
	}
	return result;
}

function deleteList() {
	if (confirm(langData.list.confirms.deleteList)) {
		$.post(apiUrl + "/DeleteList/" + global_token + '/', function (jsonString) {
			var data = jsonString;
			console.log(data);
			document.getElementById("afterLoad").style.display = "none";
			document.getElementById("listDeleted").style.display = "block";
			document.getElementById("notEditable").style.display = "none";
			
		});
		
		
	} else {
		//alert("Die Liste wurde nicht gelöscht.");
		alert(langData.list.alerts.notDeleted);
	}
}

function claimList() {
	$.ajax({
        url: apiUrl + 'ClaimList',
        type: 'POST',
        data: {
			'token': global_token
		},
        headers: {
            //'Content-Type': 'application/json; charset=utf-8;'
        },
        success: function (data) {
			data = data;
			data = data;
			console.log(data);
			if (data.hasOwnProperty("type")) {
				if (data.type == "success") {
					alert(langData.list.alerts.claimSuccess);
				} else if (data.message == "This list has a user already.") {
					alert(langData.list.alerts.claimUser);
				} else if (data.message == "No List found for this token.") {
					alert(langData.list.alerts.claimNoList);
				}
			}
        }
       });
}
