import "./FeedList.scss"

import classNames from "classnames"
import { Link } from "react-router-dom"
import { useController } from "./Controller"
import { useSessionContext } from "./Session"

export const FeedList = () => {
   const session = useSessionContext()
   const { onFeedClick } = useController()

   return (
      <div className="FeedList">
         <FeedItem title="All" count={session.unreadEntries} link="/reader/all" active={session.feedId == null && !session.onlyStarred} onClick={onFeedClick} />
         <FeedItem title="Starred" count={session.starredEntries} link="/reader/starred" active={session.feedId == null && session.onlyStarred} onClick={onFeedClick} />
         <hr />
         {session.feeds.map(feed => (
            <FeedItem key={feed.id} title={feed.userTitle || feed.title} count={feed.unreadEntries} link={`/reader/feeds/${feed.id}`} active={session.feedId === feed.id} onClick={onFeedClick} />
         ))}
      </div>
   )
}

const FeedItem = ({ title, count, active, link, onClick }) => (
   <Link className={classNames("feed", { active, hidden: !count })} to={link} onClick={onClick}>
      <span className="title">{title}</span>
      {count > 0 && (
         <span className="count">{count}</span>
      )}
   </Link>
)
