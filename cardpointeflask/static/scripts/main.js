/**
 * Prevent autoDiscover because we are creating
 * Dropzone programatically.
 */
Dropzone.autoDiscover = false;

/**
 * List of accepted file types.
 */
let acceptedFiles = ".csv, .xls, .xlsx";

/**
 * Setup Dropzone, progress bar, download button, etc.
 */
$(document).ready(function () {

  /**
   * Create custom Dropzone instance on page load.
   * 
   * @param {string} acceptedFiles - Accepted file types
   */
  function createDropzoneInstance(acceptedFiles) {
    if ($('#mydropzone').length) {
      return new Dropzone("#mydropzone", {
        dictResponseError: "Error uploading file!",
        maxFiles: 100,
        maxFilesize: 32,
        acceptedFiles: acceptedFiles,
        autoProcessQueue: false,
        uploadMultiple: true,
        addRemoveLinks: true,
        parallelUploads: 5,
        // Make sure we include the CSRF token.
        headers: {
          "X-CSRF-TOKEN": $('meta[name="csrf-token"]').attr("content"),
        },
        init: function () {
          this.on("addedfile", function (file, xhr, formData) {
            console.log("ADDED");
            this.options.acceptedFiles = acceptedFiles;
          });
          this.on("reset", function (file, xhr, formData) {
            console.log("reset");
            this.options.acceptedFiles = acceptedFiles;
            $('#buffer').empty();
          });
        },
        success: function(output, status, request) {
          // alert success
          $('#buffer').append('<div class="alert alert-success">Files successfully uploaded!</div>');

          // we will GET request from the status url for updates on our task.
          status_url = status.Location;
          update_progress(status_url, nanobar, div[0]);
        },
        error: function() {
          $('#buffer').append('<div class="alert alert-error">Unexpected error ocurred</div>');
        }
      });
    }
  }

  /**
   * Update page on the progress of our Celery task.
   * 
   * @param {string} status_url - Status API URL.
   * @param {Object} nanobar - NanoBar object.
   * @param {string} status_div - Div element where status will be displayed.
   */
  function update_progress(status_url, nanobar, status_div) {
    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
        percent = parseInt(data['current'] * 100 / data['total']);
        nanobar.go(percent);
        $(status_div.childNodes[1]).text(percent + '%');
        $(status_div.childNodes[2]).text(data['status']);
        if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
            if ('result' in data) {
                // show result
                $(status_div.childNodes[3]).text('Result: ' + data['result']);

                // enable download button
                $('#downloadFile').prop('disabled', function(index, value) { 
                  return (value ? !value : value);
                });
                // save result file to be downloaded later
                dropzone.options.responseFile = data['result'];
            }
            else {
                // something unexpected happened
                $(status_div.childNodes[3]).text('Result: ' + data['state']);
            }
        }
        else {
            // rerun every second
            setTimeout(function() {
                update_progress(status_url, nanobar, status_div);
            }, 1000);
        }
    });
  }


  /**
   * Elements for displaying the current progress.
   */
  div = $('<div class="progressBar"><div></div><div>0%</div><div>...</div><div>&nbsp;</div></div><hr>');
  $('#progress').append(div);


  /**
   * From nanobar.js, a progress bar.
   */
  var nanobar = new Nanobar({
    bg: '#44f',
    target: div[0].childNodes[0]
  });


  /**
   * Button to Process Queue once all files have been selected.
   */
  $('#processButton').click(function(e){
    e.preventDefault();           
    dropzone.processQueue();
  });


  /**
   * Button to download final file.
   */
  $('#downloadFile').click(function(e) {
    e.preventDefault();
    if (dropzone.options.responseFile) {
      var fileDownloadPath = 'export/'.concat(dropzone.options.responseFile);
      window.open(fileDownloadPath, '_blank');
    }
  });


  /**
   * Dropzone object.
   */
  let dropzone = createDropzoneInstance(acceptedFiles);
});
