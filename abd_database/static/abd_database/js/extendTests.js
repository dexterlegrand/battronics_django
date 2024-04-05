let extendTestForm = document.querySelectorAll(".upload-form")
let container = document.querySelector("#form-container")
let addButton = document.querySelector("#add-form")
let totalForms = document.querySelector("#id_form-TOTAL_FORMS")
let formNum = extendTestForm.length-1

$(document).ready(function (){
    $("#div_id_form-0-file_field").hide();
})
// $('input:file').change(
//     function(e) {
//         // for loop through all files
//         var file = e.target.files[0]
//         if (file) {
//             var reader = new FileReader();
//             reader.readAsArrayBuffer(file);
//             reader.onloadend = function (event) {
//                 var data = event.target.result;
//                 // Grab our byte length
//                 var byteLength = data.byteLength;
//
//                 // Convert to conventional array, so we can iterate though it
//                 var ui8a = new Uint8Array(data, 0);
//
//                 // Used to store each character that makes up CSV header
//                 var headerString = '';
//
//                 var isHeader = true;
//                 // Iterate through each character in our Array
//                 for (var i = 0; i < byteLength; i++) {
//                     // Get the character for the current iteration
//                     var char = String.fromCharCode(ui8a[i]);
//
//                     // Check if the char is a new line
//                     if (char.match(/[^\r\n]+/g) !== null) {
//                         if (!isHeader){
//                             // Not a new line so lets append it to our header string and keep processing
//                             headerString += char;
//                         }
//                         } else {
//                             // We found a new line character, stop processing
//                             if (!isHeader) {
//                                 break;
//                             }
//                             if (String.fromCharCode(ui8a[i+1]).match(/[^\r\n]+/g) !== null) {
//                                 isHeader = false;
//                             }
//                         }
//                     // if (char.match(/[^\r\n]+/g) !== null && !isHeader) {
//                     //
//                     //     // Not a new line so lets append it to our header string and keep processing
//                     //     headerString += char;
//                     //
//                     // } else if(!isHeader) {
//                     //     // We found a new line character, stop processing
//                     //     break;
//                     // } else{
//                     //     isHeader = false;
//                     // }
//                 }
//                 console.log(headerString);
//             }
//         }
//     });

    //     var filename = $('input[type=file]').val().split('\\').pop();
    //     console.log(filename);
    //     $.get(filename, function(data){
    //         console.log(data)
    //     }, 'text');
    //     // console.log('file "' + path.split('\\').pop() + '" selected.');
    // });
$(document).on('click', '[id^=remove-form-]', removeForm)
addButton.addEventListener('click', addForm)
container.addEventListener('change', function(e){
    if (e.target.matches("select[id^='id_form-'][id$='-extractor']")) {
        let selectedExtractor = e.target.value.toUpperCase();//$(this).children("option:selected").val();
        if (selectedExtractor != "unknown") {
            let number = e.target.id.match(/id_form-(\d+)-extractor/)[1];
            // TODO: load from UploadBatch.ExtractorTypes
            switch (selectedExtractor) {
                case "CSVEXTRACTOR":
                    $("#id_form-"+number+"-file_field").attr('accept', '.csv')
                    break;
                case "NDAEXTRACTOR":
                    $("#id_form-"+number+"-file_field").attr('accept', '.nda')
                    break;
                case "BIOLOGICEXTRACTOR":
                    $("#id_form-"+number+"-file_field").attr('accept', '.mpt')
                    break;
                case "DIGATRONEXTRACTOR":
                    $("#id_form-"+number+"-file_field").attr('accept', '.xlsx')
                    break;
                case "GAMRYEXTRACTOR":
                    $("#id_form-"+number+"-file_field").attr('accept', '.DTA')
                    break;
                default:
                    // TODO: throw error or inform user about error
                    // TODO: maybe hide filefield again
            }
            $("#div_id_form-"+number+"-file_field").show()
        }
    }
})


function addForm(e) {
    e.preventDefault()

    let newForm = extendTestForm[0].cloneNode(true) // clone form
    let formRegex = RegExp(`form-(\\d){1}-`,'g') //regex to find all instances
    formNum++ //increment formNumber
    newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${formNum}-`) //update form to have correct form number
    container.insertBefore(newForm, addButton) //insert new form at end of list of forms

    // totalForms.value = totalForms.value + 1
    totalForms.setAttribute('value', `${formNum+1}`) //increment the total number of forms
    if (formNum>0) {
        var counter = 0
        $('.upload-form hr').each(function() {
            if (!$(this).prev().is('.btn-danger'))
            {
                $(this).before('<button id="remove-form-' + counter++ + '" type="button" class="btn btn-danger">Remove Test</button>')
            }
        })
    }
}

function removeForm(e) {
    e.preventDefault()
    console.log($(e.target).parent())
    console.log("CLICKED")
    $(e.target).parent().remove()
    formNum--
    if (formNum<1) {
        $('[id^=remove-form-]').remove()
    }
}
