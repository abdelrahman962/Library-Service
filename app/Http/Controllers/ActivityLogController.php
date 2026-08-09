<?php

namespace App\Http\Controllers;
use Illuminate\Http\Request;
use Spatie\Activitylog\Models\Activity;
use App\Models\Book;
class ActivityLogController extends Controller
{
    //
    public function bookHistory(int $id){

    $book=Book::findOrFail($id);
    $activities=Activity::where('subject_type', Book::class)
        ->where('subject_id',$id)
        ->where('event','updated')
        ->get() ;


        $history=[];


        foreach($activities as $activity){
         $properties = $activity->properties;
         if (
          isset($properties['attributes']['member_id'])){
            $history[] =[
                'member_id'=>$properties['attributes']['member_id'],
                'action'=>'borrowed',
                'date'=>$activity->created_at
            ];

         }
        }
 return response()->json([

            'success'=>true,

            'book'=>$book->title,

            'history'=>$history

        ]);


    }



}
