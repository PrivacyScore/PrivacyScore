var resultColumns = ["Host", "Anzahl"];
var listData;
var langData;

$(document).ready(function() {
	var listid = getUrlVars()["list"];
	var group = getUrlVars()["group"];
	var lang = getUrlVars()["lang"];
	if (lang == null || lang.length<1) {
		lang = "de";
	}
	
	var source = 'list';
	
	if (group == null) {
		group = 0;
		listid = 0;
		source = 'scangroup';
	}
	
	
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (lang_data) {
		langData = lang_data;
		$.ajax({
				url: apiUrl + '/Statistics',
				type: 'GET',
				data: {
					'source': source,
					'sourceid': listid,
					'typet': 'third',
					"presentation": "sum"
					// 'options': {
						// 'name': 1,
						// 'description': 1,
						// 'tags': 1
					// }
				},
				// headers: {
					// 'Content-Type': 'application/json; charset=utf-8;'
				// },
				success: function (data) {
					console.log(data);
					var json = JSON.parse(data);
					console.log(json);
					callback(json);
				}
			});
	});

	
});


function callback(json){
	resultColumns = langData.thirdParties.resultColumns;
	if (json == null) {
		document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListFound;
	} else {

		fillTable(json);
		setTableSettings();
		
		var listid = getUrlVars()["list"];
		var group = getUrlVars()["group"];
		
		if (listid != null && group != null && listid.length>1 && group.length>2) {
			$.get(apiUrl + "ShowScannedList/" + listid + "/" + group, function (listJson) {
				listJson = JSON.parse(listJson);
				listData = listJson;
				setBackToListButton(listid, group);
				setListName(listJson.name);
				document.getElementById("infoGeneral").parentElement.style.display = "none";
				document.getElementById("infoList").parentElement.style.display = "block";
				document.getElementById("listName").parentElement.style.display = "block";
			});
		}

		
		document.getElementsByTagName("content").item(0).style.display = "block";
	}
	var loader = document.getElementById("loader");
	loader.style.display = "none";
}

function setTableSettings() {


	  $(document).ready(function() {
			var datatablesLanguagePath = "" + langData.lang + "_datatables.json";
			var table = $('#list_table').DataTable( {
				"responsive": true,
				"order": [[ 1, "desc" ]],
				"pagingType": "full_numbers",
				"iDisplayLength": -1,
				dom: 'rtBfip',
				language: {
					"url": datatablesLanguagePath,
					buttons: {
						pageLength: langData.scannedList.dataTables.buttonPageLength
					}
				},
				lengthMenu: [
					[5, 10, 25, -1 ],
					['5', '10', '25', 'Alle' ]
						],
				buttons: ['pageLength',
						{ extend: 'csv', text: langData.scannedList.dataTables.buttonCsv },
						{ extend: 'pdfHtml5', text: langData.scannedList.dataTables.buttonPdf}
						]
			} );
			
			$('#list_table').css( 'display', 'table' );
			
			
			//table.responsive.recalc(); // recalculate column widths

	
		} );
}

function fillTable(result) {
	var html = "<tr>";
	for (var i=0; i<resultColumns.length; i++) {
		html += "<th>";
		html += resultColumns[i];
		html += "</th>";
	}
	html += "</tr>";
	document.getElementById("list_table").getElementsByTagName("thead").item(0).innerHTML = html;
	html = "";
	for (var i=0; i<result.length; i++) {
		html += "<tr>";
		html += "<td>" + result[i].name + "</td>";
		html += "<td>" + result[i].value + "</td>";
		html += "</tr>";
	}
	document.getElementById("list_table").getElementsByTagName("tbody").item(0).innerHTML = html;
}

function setBackToListButton(list, group) {
	var button = document.getElementById("backToListButton");
	button.href = "scannedList.html?lang=" + langData.lang + "&list=" + list + "&group=" + group;
	document.getElementById("backToListButton").style.display = "inline";
}

function setListName(name) {
	var html = langData.thirdParties.list + " ";
	html += '"' + name + '"';
	document.getElementById("header").innerHTML = html;
}