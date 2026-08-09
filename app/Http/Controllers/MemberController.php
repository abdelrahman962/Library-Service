<?php

namespace App\Http\Controllers;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use App\Models\Member;
use App\Models\Book;
use Illuminate\Http\Request;
use App\Services\LibraryService;
use App\Http\Requests\StoreMemberRequest;
use App\Http\Requests\UpdateMemberRequest;
use Exception;
use Illuminate\Support\Facades\Log;
class MemberController extends Controller
{

    protected LibraryService $library;

    public function __construct(LibraryService $library)
    {
        $this->library = $library;
    }



    // GET /api/members
    public function index(Request $request)
    {

        try {


            $query = Member::with('books');


            if($request->filled('search')){


                $search = $request->search;


                $query->where(function($q) use ($search){

                    $q->where('name','like','%'.$search.'%')
                      ->orWhere('email','like','%'.$search.'%');

                });


            }



            $members = $query->paginate(5);



            return response()->json([
                'success'=>true,
                'data'=>$members
            ]);



        }catch(Exception $e){


            Log::error('Getting members failed',[
                'message'=>$e->getMessage()
            ]);


            return response()->json([
                'success'=>false,
                'message'=>'Unable to get members'
            ],500);


        }

    }




    // POST /api/members
    public function store(StoreMemberRequest $request)
    {

        try{


            $member = $this->library->addMember(
                $request->validated()
            );



            return response()->json([

                'success'=>true,

                'message'=>'Member created successfully',

                'data'=>$member

            ],201);



        }catch(Exception $e){


            Log::error('Member creation failed',[

                'message'=>$e->getMessage(),

                'line'=>$e->getLine()

            ]);



            return response()->json([

                'success'=>false,

                'message'=>'Unable to create member'

            ],500);


        }

    }





    // GET /api/members/{member}
    public function show(int $id)
    {

        try{
            $member=Member::findOrFail($id);



            $member->load('books');


            return response()->json([

                'success'=>true,

                'data'=>$member

            ]);



        }catch(Exception $e){

            Log::error('Getting member failed ',[
                'member_id'=>$id,
                'message'=>$e->getMessage()
            ]);
            return response()->json([

                'success'=>false,

                'message'=>'Unable to get member'

            ],500);


        }

    }





    // PUT /api/members/{member}
    public function update(UpdateMemberRequest $request, int $id)
    {

        try{
            $member=Member::findOrFail($id);


            $member->update(
                $request->validated()
            );


            return response()->json([

                'success'=>true,

                'message'=>'Member updated successfully',

                'data'=>$member

            ]);



        }catch(Exception $e){


            Log::error('Member update failed',[

                'member_id'=>$id,

                'message'=>$e->getMessage()

            ]);



            return response()->json([

                'success'=>false,

                'message'=>'Unable to update member'

            ],500);


        }

    }





    // DELETE /api/members/{member}
    public function destroy(int $id)
    {

        try{
            $member=Member::findOrFail($id);

            $member->delete();



            return response()->json([

                'success'=>true,

                'message'=>'Member deleted successfully'

            ]);



        }catch(Exception $e){


            Log::error('Member deletion failed',[

                'member_id'=>$id,

                'message'=>$e->getMessage()

            ]);



            return response()->json([

                'success'=>false,

                'message'=>'Unable to delete member'

            ],500);


        }

    }





    // GET /api/members/{member}/books
    // Show books that member can borrow
    public function borrowBooks(Request $request, int $id)
    {

        try{
            $member = Member::with('books')->findOrFail($id);


            $query = Book::whereNull('member_id');



            if($request->filled('search')){


                $search=$request->search;


                $query->where(function($q) use ($search){

                    $q->where('title','like','%'.$search.'%')
                      ->orWhere('category','like','%'.$search.'%');

                });


            }



            $books=$query->paginate(5);



            return response()->json([

                'success'=>true,

                'member'=>$member,

                'books'=>$books

            ]);



        }catch(Exception $e){

    Log::error('Loading borrow books failed',[

        'member_id'=>$id,

        'message'=>$e->getMessage()

    ]);


            return response()->json([

                'success'=>false,

                'message'=>'Unable to load books'

            ],500);


        }

    }






    // POST /api/members/{member}/books/{book}/borrow
    public function borrow(int $id, int $bookId)
    {

        try{
            $member=Member::findOrFail($id);

            $book=Book::findOrFail($bookId);
            $result=$this->library
                ->borrowBookForMember($member,$book);



            return response()->json([

                'success'=>$result['ok'],

                'message'=>$result['message']

            ]);



        }catch(Exception $e){


            Log::error('Borrow book failed',[

                'member_id'=>$id,

                'book_id'=>$bookId,

                'message'=>$e->getMessage()

            ]);



            return response()->json([

                'success'=>false,

                'message'=>'Unable to borrow book'

            ],500);


        }

    }







    // POST /api/members/{member}/books/{book}/return
    public function returnBook(int $id, int $bookId)
    {

        try{
            $member=Member::findOrFail($id);
            $book=Book::findOrFail($bookId);

            $result=$this->library
                ->returnBook($book,$member);


            return response()->json([

                'success'=>$result['ok'],

                'message'=>$result['message']

            ]);



        }catch(Exception $e){


            Log::error('Return book failed',[

                'member_id'=>$id,

                'book_id'=>$bookId,

                'message'=>$e->getMessage()

            ]);



            return response()->json([

                'success'=>false,

                'message'=>'Unable to return book'

            ],500);


        }

    }


}
