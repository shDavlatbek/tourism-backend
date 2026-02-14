$(document).ready(function () {
    $('.form-group')
        .find("[class*='field-description_'], [class*='field-short_description_']")
        .removeClass('col-sm-7')
        .addClass('col-sm-8');
});