import "./Reader.scss"

import { useMemo, useState } from "react"
import { EntryList } from "./EntryList"
import { EntryPager } from "./EntryPager"
import { FeedList } from "./FeedList"
import { Session } from "./Session"
import classNames from "classnames"
import { Controller } from "./Controller"

export const Reader = ({ match }) => {
   const sessionParams = useMemo(() => {
      let feedId = null
      let onlyUnread = true
      let onlyStarred = false
      if (match.path === '/reader/starred') {
         onlyUnread = false
         onlyStarred = true
      } else if (match.path === '/reader/feeds/:feedId') {
         feedId = parseInt(match.params.feedId)
      }
      return { feedId, onlyUnread, onlyStarred }
   }, [match])

   const [showSideNav, setShowSideNav] = useState(false)

   return (
      <div className={classNames("Reader", { 'show-side-nav': showSideNav })}>
         <Session params={sessionParams}>
            <Controller setShowSideNav={setShowSideNav}>
               <div className="side-nav">
                  <FeedList />
               </div>
               <div className="side-nav-toggler" onClick={() => setShowSideNav(showSideNav => !showSideNav)} />
               <div className="container">
                  <EntryList />
                  <EntryPager />
               </div>
            </Controller>
         </Session>
      </div>
   )
}
