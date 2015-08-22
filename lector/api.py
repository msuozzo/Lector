"""The javascript source for the Kindle API
"""

API_SCRIPT = """
var KindleBookMetadata = function(title, authors, asin) {
    return {
        title: title,
        authors: authors,
        asin: asin
    };
};

var KindleBookProgress = function(positions, locs, page_nums) {
    return {
        positions: positions,
        locs: locs,
        page_nums: page_nums
    };
};

var KindleAPI = (function() {

    function _get_new_kmm(modules) {
        modules = modules || [];
        var kmm = KindleModuleManagerFactory();
        // This attr makes sense seeing as BOOK_METADATA and BOOK_FRAGMAP made
        // it into the KindleModuleManager.
        kmm.BOOK_CONTEXT = "book_context";

        function copy_registration(to, from, modules) {
            modules.forEach(function(a) {
                if (!to.isModuleRegistered(a) && from.isModuleInitialized(a)) {
                    to.registerModule(a, from.getModuleSync(a));
                }
            });
        }
        copy_registration(kmm, KindleModuleManager, modules);
        return kmm;
    }

    function _load_book_modules(asin, kmm) {
        kmm = kmm || _get_new_kmm();
        kmm.BOOK_CONTEXT = "book_context";

        // Detach any attached Book data leftover
        for (var module in [kmm.BOOK_FRAGMAP, kmm.BOOK_METADATA, kmm.BOOK_CONTEXT]) {
            if (kmm.isModuleRegistered(module)) {
                kmm.detachModule(module);
            }
        }

        var modules_ready = $.Deferred();
        kmm.getModuleSync(kmm.SERVICE_CLIENT)
            .startReading({asin: asin})  // Submit ajax request for book context
            .done(function(context) {  // Register modules using this context
                kmm.registerModule(kmm.BOOK_CONTEXT, context);
                var info = KindleReaderBookInfoProvider
                                        .BookInfo({asin: null}, kmm);

                var ncp = NetworkContentProvider.create({
                    context: context,
                    bookInfo: info,
                    asin: asin
                });
                // Register metadata and fragmap
                kmm.registerModuleWithDeferred(kmm.BOOK_METADATA, ncp.getMetadata());
                kmm.registerModuleWithDeferred(kmm.BOOK_FRAGMAP, ncp.getFragmap());
                // Return the three modules
                kmm.getModuleList([kmm.BOOK_CONTEXT, kmm.BOOK_METADATA, kmm.BOOK_FRAGMAP])
                    .done(function(mods) {
                        modules_ready.resolve(mods[kmm.BOOK_CONTEXT],
                                mods[kmm.BOOK_METADATA],
                                mods[kmm.BOOK_FRAGMAP]);
                    });
            });
        return modules_ready.promise();
    }

    /*
     * Convert the larger metadata object returned by the AppDb to a
     * KindleBookMetadata object (just title, author list, and ASIN).
     */
    function _from_db_book(db_book) {
        return KindleBookMetadata(db_book.title, db_book.authors, db_book.asin);
    }

    /*
     * ASYNC
     * Return an Array of KindleBookMetadata objects representing the 
     */
    function get_library_metadata() {
        var kmm = _get_new_kmm([Kindle.MODULE.DB_CLIENT]);
        var books_ready = $.Deferred();
        kmm.getModuleSync(Kindle.MODULE.DB_CLIENT)
            .getAppDb()
            .getAllBooks()
            .done(function(books) {
                books_ready.resolve($.map(books, _from_db_book));
            });
        return books_ready.promise();
    }

    /*
     * ASYNC
     * Return the KindleBookMetadata object for the book associated with `asin`
     */
    function get_book_metadata(asin) {
        var kmm = _get_new_kmm([Kindle.MODULE.DB_CLIENT]);
        var book_ready = $.Deferred();
        kmm.getModuleSync(Kindle.MODULE.DB_CLIENT)
            .getAppDb()
            .getBook(asin, function(db_book) {
                book_ready.resolve(_from_db_book(db_book));
            });
        return book_ready;
    }

    /*
     * ASYNC
     * Return the KindleBookProgress object for the book associated with `asin`
     */
    function get_book_progress(asin) {
        // A new ModuleManager is constructed for each call to this function
        // so that calls can be made concurrently (e.g. in
        // get_library_progress())
        var kmm = _get_new_kmm([Kindle.MODULE.DB_CLIENT,
                                Kindle.MODULE.SERVICE_CLIENT,
                                Kindle.MODULE.METRICS_MANAGER,
                                Kindle.MODULE.PageNumberManager]);

        var book_ready = $.Deferred();
        _load_book_modules(asin, kmm)
            .done(function(context, metadata) {
                var info = KindleReaderBookInfoProvider
                                        .BookInfo({asin: metadata.asin}, kmm);
                var current = info.getFurthestPositionReadData().position,
                    start = metadata.startPosition,
                    end = metadata.endPosition;
                var positions = [start, current, end];

                // Convert positions to Location and Page Number (if available)
                var locs_dfd = $.map(positions, info.getLocationConverter().locationFromPosition);
                var loc_conversions = $.when.apply($, locs_dfd);

                var page_conversions = $.Deferred();
                if (context.pageNumberUrl) {
                    info.getContext = function() { return context; };
                    var pgnum_dfd = kmm
                                .getModuleSync(Kindle.MODULE.PageNumberManager)
                                .getPageNumbers(info);
                    pgnum_dfd.done(function(pageConverter) {
                        var range_obj = pageConverter.getPageNumberRanges().arabic;
                        var range = [range_obj.minPage, range_obj.maxPage];
                        // Ensure position is within the valid page range
                        var position_range = $.map(range, pageConverter.positionFromPageNumber);
                        if (position_range[0] == -1 || position_range[1] == -1) {
                            // Page conversion error
                            page_conversions.resolve(void 0);
                        } else {
                            var corrected_position = (current < position_range[0]) ? position_range[0]
                                                    : (current > position_range[1]) ? position_range[1]
                                                    : current;
                            var curr_page = pageConverter.pageNumberFromPosition(corrected_position);
                            page_conversions.resolve([range_obj.minPage,
                                                        parseInt(curr_page),
                                                        range_obj.maxPage]);
                        }
                    });
                } else {
                    page_conversions.resolve(void 0);
                }

                $.when(loc_conversions, page_conversions)
                    .done(function (locs, page_nums) {
                        book_ready.resolve(KindleBookProgress(positions, locs, page_nums));
                    });
            });
        return book_ready.promise();
    }

    /*
     * ASYNC
     * Return an object where each attribute is an ASIN from the user's
     * library and the value is the associated KindleBookProgress object.
     */
    function get_library_progress() {
        var books_ready = $.Deferred();
        get_library_metadata().done(function(books) {
            var asins = $.map(books, function(book) { return book.asin; });
            $.when.apply($, $.map(asins, get_book_progress)).done(function() {
                var progress_list = arguments;
                var ret = {};
                asins.map(function(asin, i) {
                    ret[asin] = progress_list[i];
                });
                books_ready.resolve(ret);
            });
        });
        return books_ready.promise();
    }

    return {
        get_book_progress: get_book_progress,
        get_library_progress: get_library_progress,
        get_book_metadata: get_book_metadata,
        get_library_metadata: get_library_metadata
    };
})();
"""
