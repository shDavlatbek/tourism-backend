(function ($) {
    // Safely check if jQuery is available
    if (!$) {
        // Try to find jQuery in window if not passed
        $ = window.django ? window.django.jQuery : (window.jQuery || undefined);
    }

    if (!$) {
        console.error("django.jQuery not found! Please ensure admin/js/jquery.init.js is loaded.");
        return;
    }

    $(document).ready(function () {
        // Function to customize add row buttons
        function customizeAddButton($group, buttonText) {
            if (!$group.length) return;

            // Find the add-row link
            var $addRow = $group.find('.add-row a');

            // Add classes if not already present
            if (!$addRow.hasClass('btn')) {
                $addRow.addClass('btn btn-sm btn-default float-right');
                $addRow.attr('role', 'button');

                // Update text if provided
                if (buttonText) {
                    $addRow.text(buttonText);
                }
            }
        }

        // Try to find the groups using related_name first, then default set names
        var $galleryGroup = $('#gallery-group');
        if (!$galleryGroup.length) $galleryGroup = $('#gallery_set-group');

        var $commentGroup = $('#comments-group');
        if (!$commentGroup.length) $commentGroup = $('#comment_set-group');

        // Customize Gallery Inline
        if ($galleryGroup.length) {
            customizeAddButton($galleryGroup, "Add another Galereya");

            // Check for .inline-related that are NOT the empty template
            // Django's empty form usually has class 'empty-form' and also 'inline-related'
            if ($galleryGroup.find('.inline-related:not(.empty-form)').length === 0) {
                console.log("No visible gallery rows found, clicking add button...");
                $galleryGroup.find('.add-row a').click();

                var $dynamicGallery = $('.dynamic-gallery .select2-container--default');
                if ($dynamicGallery.length) {
                    $dynamicGallery.remove();
                } else {
                    setTimeout(() => {
                        $dynamicGallery.remove();
                    }, 1000);
                }
            }
        }

        // Customize Comment Inline
        if ($commentGroup.length) {
            customizeAddButton($commentGroup, "Add another Comment");

            if ($commentGroup.find('.inline-related:not(.empty-form)').length === 0) {
                console.log("No visible comment rows found, clicking add button...");
                $commentGroup.find('.add-row a').click();
            }
        }
    });
})(window.django ? window.django.jQuery : undefined);
