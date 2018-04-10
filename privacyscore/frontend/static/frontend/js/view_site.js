function toggleIcon(e) {
    $(e.target)
        .prev('.panel-heading')
        .find(".more-less")
        .toggleClass('glyphicon-menu-down glyphicon-menu-up');
}
$('.panel-group').on('hidden.bs.collapse', toggleIcon);
$('.panel-group').on('shown.bs.collapse', toggleIcon);

$(function() {
    $('#disclaimer-link').on('click', function() {
        $('#disclaimer').show();
        $(this).hide();
    })
});
