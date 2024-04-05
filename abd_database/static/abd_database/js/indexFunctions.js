// Code By Webdevtrick ( https://webdevtrick.com )
$(document).ready(function() {
// Setup - add a text input to each footer cell
    $('#sort tfoot th').each( function () {
        var title = $(this).text();
        $(this).html( '<input type="text" placeholder="Search '+title+'" />' );
    } );
//    mehr schlecht als recht!
    $("input[placeholder]").each(function () {
        $(this).attr('size', $(this).attr('placeholder').length - 2);
    });
   // DataTable
    var table = $('#sort').DataTable({
        initComplete: function () {
            // Apply the search
            this.api().columns().every( function () {
                var that = this;

                $( 'input', this.footer() ).on( 'keyup change clear', function () {
                    if ( that.search() !== this.value ) {
                        that
                            .search( this.value )
                            .draw();
                    }
                } );
            } );
        }
    });
});
