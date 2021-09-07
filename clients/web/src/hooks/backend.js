import axios from "axios"
import { useEffect, useMemo, useState } from "react"


const useQuery = (query, variables) => {
   const [loading, setLoading] = useState(false)
   const [data, setData] = useState(null)

   useEffect(() => {
      let cancelRequest

      setLoading(true)

      axios({
         url: '/graphql',
         method: 'post',
         data: { query, variables },
         cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
      }).then(response => {
         setData(response.data.data)
         setLoading(false)
      }).catch(error => {
         if (axios.isCancel(error)) {
            return
         }
      })

      return () => {
         cancelRequest()
      }
   }, [query, variables])

   return { loading, data }
}

const entryFields = `
   id
   title
   link
   summary { value }
   content { value }
   publishText
   publishTime
   readTime
   starTime
`

export const useEntries = (entryIds) => {
   const variables = useMemo(() => ({ entryIds }), [entryIds])
   const { loading, data } = useQuery(`
      query ($entryIds: [Int]!) {
         entries(entryIds: $entryIds) {
            ${entryFields}
         }
      }
   `, variables)

   return { loading, entries: data?.entries || [] }
}

export const useFeeds = () => {
   const { loading, data } = useQuery(`
      query {
         feeds {
            id
            title
            userTitle
            unreadEntries
         }
      }
   `)

   return { loading, feeds: data?.feeds || [] }
}

export const useSession = ({ feedId, onlyUnread, onlyStarred, firstEntries }) => {
   const variables = useMemo(() => ({ feedId, onlyUnread, onlyStarred, firstEntries }), [feedId, onlyUnread, onlyStarred, firstEntries])
   const { loading, data } = useQuery(`
      query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $firstEntries: Int!) {
         session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred) {
            entries(first: $firstEntries) {
               ${entryFields}
            }
            entryIds
            feeds {
               id
               title
               userTitle
               unreadEntries
            }
         }
      }
   `, variables)

   return { loading, session: data?.session }
}
