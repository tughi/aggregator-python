import "./Reader.scss"

import classNames from "classnames"
import { useState } from "react"
import { Controller } from "./Controller"
import { EntryList } from "./EntryList"
import { EntryViewer } from "./EntryViewer"
import { FeedList } from "./FeedList"

export const Reader = () => {
   const [showSideNav, setShowSideNav] = useState(false)

   return (
      <div className={classNames("Reader", { 'show-side-nav': showSideNav })}>
         <Controller setShowSideNav={setShowSideNav}>
            <div className="side-nav">
               <FeedList />
            </div>
            <div className="main">
               <EntryList />
               <EntryViewer />
            </div>
         </Controller>
      </div>
   )
}
