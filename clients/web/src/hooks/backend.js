import axios from "axios"
import { useCallback, useEffect, useMemo, useState } from "react"

const useQuery = ({ query, variables, consumeData, ignore }) => {
   const [loading, setLoading] = useState(false)

   useEffect(() => {
      if (!ignore) {
         let cancelRequest

         setLoading(true)

         axios({
            url: '/graphql',
            method: 'post',
            data: { query, variables },
            cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
         }).then(response => {
            setLoading(false)
            consumeData(response.data.data)
         }).catch(error => {
            if (axios.isCancel(error)) {
               return
            }
         })

         return () => {
            cancelRequest()
         }
      }
   }, [query, variables, consumeData, ignore])

   return loading
}

export const useSession = ({ sessionTime, feedId, onlyUnread, onlyStarred, entriesLimit = 50 }) => {
   const [feeds, setFeeds] = useState([])
   const [feedsById, setFeedsById] = useState({})
   const [unreadEntries, setUnreadEntries] = useState(0)
   const [starredEntries, setStarredEntries] = useState(0)
   const [entryIds, setEntryIds] = useState([])
   const [entries, setEntries] = useState([])

   const [entriesOffset, setEntriesOffset] = useState(0)

   const sessionQueryVariables = useMemo(() => {
      if (sessionTime) {
         return { feedId, onlyUnread, onlyStarred, entriesLimit }
      }
   }, [sessionTime, feedId, onlyUnread, onlyStarred, entriesLimit])

   useEffect(() => {
      setEntryIds([])
      setEntries([])
      setEntriesOffset(0)
   }, [sessionQueryVariables])

   const consumeSessionData = useCallback(({ session }) => {
      setFeeds(session.feeds)
      setFeedsById(session.feeds.reduce((feedsById, feed) => ({ ...feedsById, [feed.id]: feed })))
      setUnreadEntries(session.unreadEntries)
      setStarredEntries(session.starredEntries)
      setEntryIds(session.entryIds)
      setEntries(session.entries)
   }, [])

   const sessionIsLoading = useQuery({
      query: `query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!) {
         session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred) {
            entries(limit: $entriesLimit) {
               id
               feedId
               title
               link
               summary { value }
               content { value }
               author { name }
               publishText
               publishTime
               readTime
               starTime
            }
            entryIds
            feeds {
               id
               faviconUrl
               title
               userTitle
               unreadEntries
            }
            unreadEntries
            starredEntries
         }
      }`,
      variables: sessionQueryVariables,
      consumeData: consumeSessionData,
   })

   const entriesQueryVariables = useMemo(() => ({ entryIds: entryIds.slice(entriesOffset, entriesOffset + entriesLimit) }), [entryIds, entriesOffset, entriesLimit])

   const consumeEntriesData = useCallback(({ entries }) => {
      setEntries(currentEntries => [...currentEntries, ...entries])
   }, [])

   const entriesAreLoading = useQuery({
      query: `query ($entryIds: [Int]!) {
         entries(entryIds: $entryIds) {
            id
            feedId
            title
            link
            summary { value }
            content { value }
            author { name }
            publishText
            publishTime
            readTime
            starTime
         }
      }`,
      variables: entriesQueryVariables,
      consumeData: consumeEntriesData,
      ignore: entriesOffset === 0,
   })

   const loadMoreEntries = useCallback(() => {
      setEntriesOffset(entries.length)
   }, [entries])

   return {
      isLoading: sessionIsLoading || entriesAreLoading,
      feeds,
      feedsById,
      entryIds,
      entries,
      unreadEntries,
      starredEntries,
      hasMoreEntries: entries.length < entryIds.length,
      loadMoreEntries,
   }
}
