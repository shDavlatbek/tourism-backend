document.addEventListener('DOMContentLoaded', function () {
    // Select all inputs that start with 'activities' or 'seo_tags' to support modeltranslation (e.g., activities_uz, seo_tags_ru)
    var inputs = document.querySelectorAll('input[name^="activities"], input[name^="seo_tags"]');

    inputs.forEach(function (input) {
        new Tagify(input, {
            // Converts the Tagify output back to a simple comma-separated string
            // so our Django backend `clean()` functions can process it normally.
            originalInputValueFormat: valuesArr => valuesArr.map(item => item.value).join(', ')
        });
    });
});
