@if ($paginator->hasPages())
    <nav role="navigation" aria-label="Pagination Navigation">
        <div>
            <p>
                Showing {{ $paginator->firstItem() }} to {{ $paginator->lastItem() }} of {{ $paginator->total() }} results
            </p>

            <div>
                @if ($paginator->onFirstPage())
                    <span>Previous</span>
                @else
                    <a href="{{ $paginator->previousPageUrl() }}" rel="prev">Previous</a>
                @endif

                @foreach ($elements as $element)
                    @if (is_string($element))
                        <span>{{ $element }}</span>
                    @endif

                    @if (is_array($element))
                        @foreach ($element as $page => $url)
                            @if ($page == $paginator->currentPage())
                                <span>{{ $page }}</span>
                            @else
                                <a href="{{ $url }}">{{ $page }}</a>
                            @endif
                        @endforeach
                    @endif
                @endforeach

                @if ($paginator->hasMorePages())
                    <a href="{{ $paginator->nextPageUrl() }}" rel="next">Next</a>
                @else
                    <span>Next</span>
                @endif
            </div>
        </div>
    </nav>
@endif
